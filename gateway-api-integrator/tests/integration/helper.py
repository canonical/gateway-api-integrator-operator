# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper methods for integration tests."""

import json
from urllib.parse import ParseResult, urlparse

import jubilant
import lightkube
from lightkube.generic_resource import GenericNamespacedResource, create_namespaced_resource
from requests.adapters import DEFAULT_POOLBLOCK, DEFAULT_POOLSIZE, DEFAULT_RETRIES, HTTPAdapter

GATEWAY_API_GROUP = "gateway.networking.k8s.io"
GATEWAY_RESOURCE_NAME = "Gateway"
GATEWAY_PLURAL = "gateways"
HTTP_ROUTE_RESOURCE_NAME = "HTTPRoute"
HTTP_ROUTE_PLURAL = "httproutes"


class DNSResolverHTTPSAdapter(HTTPAdapter):
    """A simple mounted DNS resolver for HTTP requests."""

    def __init__(
        self,
        hostname,
        ip,
    ):
        """Initialize the dns resolver.

        Args:
            hostname: DNS entry to resolve.
            ip: Target IP address.
        """
        self.hostname = hostname
        self.ip = ip
        super().__init__(
            pool_connections=DEFAULT_POOLSIZE,
            pool_maxsize=DEFAULT_POOLSIZE,
            max_retries=DEFAULT_RETRIES,
            pool_block=DEFAULT_POOLBLOCK,
        )

    # Ignore pylint rule as this is the parent method signature
    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):  # pylint: disable=too-many-arguments, too-many-positional-arguments
        """Wrap HTTPAdapter send to modify the outbound request.

        Args:
            request: Outbound HTTP request.
            stream: argument used by parent method.
            timeout: argument used by parent method.
            verify: argument used by parent method.
            cert: argument used by parent method.
            proxies: argument used by parent method.

        Returns:
            Response: HTTP response after modification.
        """
        connection_pool_kwargs = self.poolmanager.connection_pool_kw

        result = urlparse(request.url)
        if result.hostname == self.hostname:
            ip = self.ip
            if result.scheme == "https" and ip:
                request.url = request.url.replace(
                    "https://" + result.hostname,
                    "https://" + ip,
                )
                connection_pool_kwargs["server_hostname"] = result.hostname
                connection_pool_kwargs["assert_hostname"] = result.hostname
                request.headers["Host"] = result.hostname
            else:
                connection_pool_kwargs.pop("server_hostname", None)
                connection_pool_kwargs.pop("assert_hostname", None)

        return super().send(request, stream, timeout, verify, cert, proxies)


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
    ingress_requirer_application: str, juju: jubilant.Juju
) -> ParseResult:
    """Get the ingress url from the requirer's unit data.

    Args:
        ingress_requirer_application: Name of the requirer application.
        juju: Jubilant Juju instance.

    Returns:
        ParseResult: The parsed ingress url.
    """
    unit_name = f"{ingress_requirer_application}/0"
    stdout = juju.cli("show-unit", unit_name, "--format", "json")
    unit_information = json.loads(stdout)[unit_name]
    ingress_integration_data = json.loads(
        unit_information["relation-info"][0]["application-data"]["ingress"]
    )
    return urlparse(ingress_integration_data["url"])
