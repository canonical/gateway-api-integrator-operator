# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for testing both charms."""

import ipaddress

import jubilant
import requests
import urllib3
import yaml
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings when using verify=False
urllib3.disable_warnings(InsecureRequestWarning)


def get_url_from_relation(juju: jubilant.Juju, unit_name: str) -> str:
    """Get the ingress url from the units relation data.

    Args:
        juju (jubilant.Juju): The jubilant Juju instance.
        unit_name (str): The target unit's name.

    Returns:
        str: The ingress IP address.
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
        juju (jubilant.Juju): The jubilant Juju instance.
        gateway_api_integrator (str): The gateway-api-integrator app name.

    Returns:
        str: The gateway IP address.
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


def test_http(
    juju: jubilant.Juju,
    ingress_configurator: str,
    gateway_api_integrator_no_tls: str,
    gateway_route_backend_application: str,
):
    """Test that the gateway-api-integrator charm can route HTTP traffic to a backend application."""
    juju.integrate(
        f"{ingress_configurator}:ingress",
        f"{gateway_route_backend_application}:ingress",
    )
    juju.integrate(
        f"{gateway_api_integrator_no_tls}:gateway-route",
        f"{ingress_configurator}:gateway-route",
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status,
            ingress_configurator,
            gateway_route_backend_application,
            gateway_api_integrator_no_tls,
        ),
        timeout=600,
    )

    # send a request to verify routing
    gateway_address = get_gateway_ip(juju, gateway_api_integrator_no_tls)
    response = requests.get(
        f"http://{gateway_address}/app1",
        timeout=10,
        headers={"Host": "www.gateway.internal"},
    )
    assert response.status_code == 200
    assert "Welcome to flask-k8s Charm" in response.text

    juju.config(ingress_configurator, reset="hostname")
    juju.wait(
        lambda status: jubilant.all_active(
            status,
            ingress_configurator,
            gateway_route_backend_application,
            gateway_api_integrator_no_tls,
        ),
        timeout=600,
    )
    response = requests.get(
        f"http://{gateway_address}/app1",
        timeout=10,
    )
    assert response.status_code == 200
    assert "Welcome to flask-k8s Charm" in response.text
