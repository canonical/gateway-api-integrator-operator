# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Shared helpers for e2e tests."""

import ipaddress

import jubilant
import requests
import urllib3
import yaml
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_fixed
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings when using verify=False
urllib3.disable_warnings(InsecureRequestWarning)


@retry(
    stop=stop_after_delay(180),
    wait=wait_fixed(5),
    retry=retry_if_exception_type((AssertionError, requests.exceptions.RequestException)),
    reraise=True,
)
def assert_gateway_route_response(
    gateway_address: str,
    hostname: str | None,
    path: str,
    *,
    scheme: str = "https",
    expected_status: int = 200,
    body_contains: str | None = None,
) -> requests.Response:
    """Get a gateway route and assert expected response, retrying while dataplane converges."""
    headers = {"Host": hostname} if hostname is not None else None
    response = requests.get(
        f"{scheme}://{gateway_address}{path}",
        verify=False,
        timeout=10,
        headers=headers,
    )

    assert response.status_code == expected_status, (
        f"Failed to route to {hostname}: status={response.status_code}, "
        f"expected={expected_status}, body={response.text!r}"
    )
    if body_contains is not None:
        assert body_contains in response.text, (
            f"Expected response body for {hostname} to contain {body_contains!r}, "
            f"body={response.text!r}"
        )

    return response


def get_url_from_relation(juju: jubilant.Juju, unit_name: str) -> str:
    """Get the ingress url from the units relation data.

    Args:
        juju: The jubilant Juju instance.
        unit_name: The target unit's name.

    Returns:
        The ingress URL.
    """
    unit_data = yaml.safe_load(juju.cli("show-unit", unit_name))

    for relation in unit_data[unit_name]["relation-info"]:
        if relation["endpoint"] == "ingress":
            # app data is encoded as a string so we have to load it as yaml again :(
            return yaml.safe_load(relation["application-data"]["ingress"])["url"]
    return ""


def get_gateway_ip(juju: jubilant.Juju, gateway_api_integrator: str) -> str:
    """Get the gateway IP from the charm status message.

    Args:
        juju: The jubilant Juju instance.
        gateway_api_integrator: The gateway-api-integrator app name.

    Returns:
        The gateway IP address.
    """
    status = juju.status()
    app_status = status.apps[gateway_api_integrator]
    message = app_status.app_status.message
    if "gateway address" in message.lower():
        parts = message.split()
        try:
            candidate = parts[2]
            ipaddress.IPv4Address(candidate)
            return candidate
        except (IndexError, ipaddress.AddressValueError):
            return ""
    return ""


def get_gateway_route_provider_data(
    juju: jubilant.Juju, unit_name: str
) -> dict:
    """Get the gateway-route provider application data from the relation.

    Args:
        juju: The jubilant Juju instance.
        unit_name: The target unit's name.

    Returns:
        The provider application data dictionary.
    """
    unit_data = yaml.safe_load(juju.cli("show-unit", unit_name))

    for relation in unit_data[unit_name]["relation-info"]:
        if relation["endpoint"] == "gateway-route":
            return relation["application-data"]
    return {}
