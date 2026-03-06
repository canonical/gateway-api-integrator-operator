# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for testing both charms."""

import jubilant
import requests
import urllib3
import yaml
from urllib3.exceptions import InsecureRequestWarning

from .conftest import App  # pylint: disable=no-name-in-module

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


def get_gateway_ip(juju: jubilant.Juju, gateway_api_integrator: App) -> str:
    """Get the gateway IP from the charm status message.

    Args:
        juju (jubilant.Juju): The jubilant Juju instance.
        gateway_api_integrator (App): The gateway-api-integrator app.

    Returns:
        str: The gateway IP address.
    """
    status = juju.status()
    app_status = status.apps[gateway_api_integrator.name]
    message = app_status.app_status.message
    if "gateway address" in message.lower():
        # Extract IP from message
        parts = message.split(":")
        ip = parts[1].strip()
        return ip
    return ""


def test_http(
    juju: jubilant.Juju,
    gateway_route_configurator: App,
    gateway_api_integrator_no_tls: str,
    gateway_route_backend_application: str,
):
    """Test that the gateway-api-integrator charm can route HTTP traffic to a backend application."""
    juju.integrate(
        f"{gateway_route_configurator.name}:ingress",
        f"{gateway_route_backend_application}:ingress",
    )
    juju.integrate(
        f"{gateway_api_integrator_no_tls}:gateway-route",
        f"{gateway_route_configurator.name}:gateway-route",
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status,
            gateway_route_configurator.name,
            gateway_route_backend_application,
            gateway_api_integrator_no_tls,
        ),
        timeout=600,
    )

    # send a request to verify routing
    gateway_address = get_gateway_ip(juju, App(gateway_api_integrator_no_tls))
    response = requests.get(
        f"http://{gateway_address}/app1",
        timeout=10,
        headers={"Host": "www.gateway.internal"},
    )
    assert response.status_code == 200
    assert "Welcome to flask-k8s Charm" in response.text

    juju.config(gateway_route_configurator.name, reset="hostname")
    response = requests.get(
        f"http://{gateway_address}/app1",
        timeout=10,
    )
    assert response.status_code == 200
    assert "Welcome to flask-k8s Charm" in response.text
