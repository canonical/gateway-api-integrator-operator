# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper methods for integration tests."""

import json
from urllib.parse import ParseResult, urlparse

import jubilant
import lightkube
import requests
from lightkube.generic_resource import GenericNamespacedResource, create_namespaced_resource
from requests.adapters import DEFAULT_POOLBLOCK, DEFAULT_POOLSIZE, DEFAULT_RETRIES, HTTPAdapter
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_fixed


class DNSResolverAdapter(HTTPAdapter):
    """A requests transport adapter that routes a hostname to a fixed IP.

    Lets ``requests`` connect to a known IP while sending the correct SNI and
    Host header, which hostname-scoped Gateway listeners require.
    """

    def __init__(self, hostname: str, ip: str) -> None:
        """Initialise the adapter.

        Args:
            hostname: The DNS name to intercept.
            ip: The IP address to route to instead.
        """
        self.hostname = hostname
        self.ip = ip
        super().__init__(
            max_retries=DEFAULT_RETRIES,
            pool_connections=DEFAULT_POOLSIZE,
            pool_maxsize=DEFAULT_POOLSIZE,
            pool_block=DEFAULT_POOLBLOCK,
        )

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):  # pylint: disable=too-many-arguments, too-many-positional-arguments
        """Intercept the request and rewrite the URL to use the target IP.

        Args:
            request: Outbound HTTP request.
            stream: Passed through to the parent.
            timeout: Passed through to the parent.
            verify: Passed through to the parent.
            cert: Passed through to the parent.
            proxies: Passed through to the parent.

        Returns:
            The HTTP response.
        """
        connection_pool_kwargs = self.poolmanager.connection_pool_kw
        result = urlparse(request.url)
        if result.hostname == self.hostname:
            if result.scheme == "http" and self.ip:
                request.url = request.url.replace("http://" + result.hostname, "http://" + self.ip)
                connection_pool_kwargs["server_hostname"] = result.hostname
                request.headers["Host"] = result.hostname
            elif result.scheme == "https" and self.ip:
                request.url = request.url.replace(
                    "https://" + result.hostname, "https://" + self.ip
                )
                connection_pool_kwargs["server_hostname"] = result.hostname
                connection_pool_kwargs["assert_hostname"] = result.hostname
                request.headers["Host"] = result.hostname
            else:
                connection_pool_kwargs.pop("server_hostname", None)
                connection_pool_kwargs.pop("assert_hostname", None)
        return super().send(request, stream, timeout, verify, cert, proxies)


GATEWAY_API_GROUP = "gateway.networking.k8s.io"
GATEWAY_RESOURCE_NAME = "Gateway"
GATEWAY_PLURAL = "gateways"
HTTP_ROUTE_RESOURCE_NAME = "HTTPRoute"
HTTP_ROUTE_PLURAL = "httproutes"


def get_gateway_resource(
    lightkube_client: lightkube.Client,
    application_name: str,
) -> GenericNamespacedResource:
    """Get the Gateway custom resource for a gateway-api-integrator application.

    Args:
        lightkube_client: Initialized lightkube client.
        application_name: Name of the gateway-api-integrator application.

    Returns:
        The Gateway custom resource.
    """
    gateway_class = create_namespaced_resource(
        GATEWAY_API_GROUP, "v1", GATEWAY_RESOURCE_NAME, GATEWAY_PLURAL
    )
    return lightkube_client.get(gateway_class, name=application_name)


def get_http_route_resource(
    lightkube_client: lightkube.Client,
    application_name: str,
    route_type: str = "http",
) -> GenericNamespacedResource:
    """Get an HTTPRoute custom resource for a gateway-api-integrator application.

    Args:
        lightkube_client: Initialized lightkube client.
        application_name: Name of the gateway-api-integrator application.
        route_type: The route type suffix, either 'http' or 'https'.

    Returns:
        The HTTPRoute custom resource.
    """
    http_route_class = create_namespaced_resource(
        GATEWAY_API_GROUP, "v1", HTTP_ROUTE_RESOURCE_NAME, HTTP_ROUTE_PLURAL
    )
    return lightkube_client.get(http_route_class, name=f"{application_name}-{route_type}")


def get_ingress_url_for_application(
    ingress_requirer_application: str, ingress_provider_application: str, juju: jubilant.Juju
) -> ParseResult:
    """Get the ingress url from the requirer's unit data.

    Passing both the requirer and provider application names is necessary because the unit name to query differs between Juju 3 and 4.
    In Juju 3, the requirer's unit is queried, while in Juju 4, the provider's unit is queried.

    Args:
        ingress_requirer_application: Name of the requirer application.
        ingress_provider_application: Name of the provider application.
        juju: Jubilant Juju instance.

    Returns:
        ParseResult: The parsed ingress url.
    """
    # Differentiate between Juju 3 and Juju 4 to determine which unit to query for the ingress url.
    # Issue: https://github.com/juju/juju/issues/22796
    if juju.version().major >= 4:
        unit_name = f"{ingress_provider_application}/0"
        stdout = juju.cli(
            "show-unit",
            unit_name,
            "--format",
            "json",
            "--related-unit",
            f"{ingress_requirer_application}/0",
            "--endpoint",
            "gateway",
        )
    else:
        unit_name = f"{ingress_requirer_application}/0"
        stdout = juju.cli(
            "show-unit",
            unit_name,
            "--format",
            "json",
            "--related-unit",
            f"{ingress_provider_application}/0",
            "--endpoint",
            "ingress",
        )
    unit_information = json.loads(stdout)[unit_name]
    ingress_integration_data = json.loads(
        unit_information["relation-info"][0]["application-data"]["ingress"]
    )
    return urlparse(ingress_integration_data["url"])


@retry(
    stop=stop_after_delay(180),
    wait=wait_fixed(5),
    retry=retry_if_exception_type((AssertionError, requests.exceptions.RequestException)),
    reraise=True,
)
def wait_for_response(
    url: str,
    *,
    hostname: str,
    ip: str,
    expected_status: int,
    body_contains: str | None = None,
    timeout: int | float = 30,
    **kwargs,
) -> requests.Response:
    """Retry HTTP GET until expected status/body is observed.

    When *hostname* differs from the host in *url* (e.g. the URL contains a
    bare IP), the URL is rewritten to use *hostname* and a
    :class:`DNSResolverAdapter` is mounted so the TCP connection still goes to
    *ip*. This ensures TLS SNI matches the ``hostname:`` field on the Gateway
    listener.
    """
    headers = kwargs.pop("headers", {})
    headers.setdefault("Host", hostname)

    parsed = urlparse(url)
    session = requests.Session()
    if hostname and ip and parsed.hostname != hostname:
        port = parsed.port
        new_netloc = f"{hostname}:{port}" if port else hostname
        url = parsed._replace(netloc=new_netloc).geturl()
        session.mount(f"{parsed.scheme}://{hostname}", DNSResolverAdapter(hostname, ip))
    response = session.get(url, timeout=timeout, headers=headers, **kwargs)

    assert response.status_code == expected_status, (
        f"Unexpected status from {url}. "
        f"got={response.status_code}, expected={expected_status}, body={response.text!r}"
    )

    if body_contains:
        assert body_contains in response.text, (
            f"Expected response body from {url} to contain {body_contains!r}. "
            f"body={response.text!r}"
        )

    return response
