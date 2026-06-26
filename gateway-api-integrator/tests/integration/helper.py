# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper methods for integration tests."""

import json
from urllib.parse import ParseResult, urlparse

import jubilant
import lightkube
import requests
from lightkube.generic_resource import GenericNamespacedResource, create_namespaced_resource
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_fixed

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
    """Retry HTTP GET until expected status/body is observed."""
    headers = kwargs.pop("headers", {})
    headers.setdefault("Host", hostname)
    response = requests.get(url, timeout=timeout, headers=headers, **kwargs)

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
