# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for testing both charms."""

import ipaddress

import jubilant
import yaml
from .helper import assert_gateway_route_response


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


def test_configurator(
    juju: jubilant.Juju,
    ingress_configurator: str,
    gateway_api_integrator: str,
    gateway_route_backend_application: str,
    external_hostname: str,
):
    """
    Test that the charms correctly set up the gateway route relation.
    Deploy ingress-configurator and integrate it on gateway-route relation.
    Assert that a request to the external hostname is correctly routed to the any-charm app
    """

    juju.integrate(
        f"{ingress_configurator}:ingress",
        f"{gateway_route_backend_application}:ingress",
    )
    juju.integrate(
        f"{gateway_api_integrator}:gateway-route",
        f"{ingress_configurator}:gateway-route",
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, ingress_configurator, gateway_route_backend_application, gateway_api_integrator
        ),
        timeout=600,
    )

    # send a request to verify routing
    gateway_address = get_gateway_ip(juju, gateway_api_integrator)

    # HTTPS
    assert_gateway_route_response(
        gateway_address,
        external_hostname,
        "/app1/",
        body_contains="Hello from any_charm",
    )
    assert get_url_from_relation(juju, f"{gateway_route_backend_application}/0") == f"https://{external_hostname}/app1"

    # HTTP with hostname
    juju.config(gateway_api_integrator, {"enforce-https": False})
    juju.wait(
        lambda status: jubilant.all_active(
            status, ingress_configurator, gateway_route_backend_application, gateway_api_integrator
        ),
        timeout=600,
    )

    assert_gateway_route_response(
        gateway_address,
        external_hostname,
        "/app1/",
        body_contains="Hello from any_charm",
    )
