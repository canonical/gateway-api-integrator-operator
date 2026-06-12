# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for testing both charms."""

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
        # Extract IP from message
        parts = message.split(":")
        ip = parts[1].strip()
        return ip
    return ""


def test_configurator(
    juju: jubilant.Juju,
    ingress_configurator: str,
    gateway_api_integrator: str,
    external_hostname: str,
):
    """
    Test that the charms correctly set up the gateway route relation.
    Deploy ingress-configurator and integrate it on gateway-route relation.
    Assert that a request to the external hostname is correctly routed to the flask-k8s app
    """
    additional_hostnames = ["gateway-alt.internal", "gateway-alt2.internal"]
    juju.config(
        ingress_configurator,
        {"additional-hostnames": ",".join(additional_hostnames)},
    )

    juju.deploy(
        "flask-k8s",
        channel="latest/edge",
    )

    juju.integrate(
        f"{ingress_configurator}:ingress",
        "flask-k8s:ingress",
    )
    juju.integrate(
        f"{gateway_api_integrator}:gateway-route",
        f"{ingress_configurator}:gateway-route",
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, ingress_configurator, "flask-k8s", gateway_api_integrator
        ),
        timeout=600,
    )

    # send a request to verify routing
    gateway_address = get_gateway_ip(juju, gateway_api_integrator)

    # HTTPS
    response = requests.get(
        f"https://{gateway_address}/app1",
        verify=False,
        timeout=10,
        headers={"Host": external_hostname},
    )
    assert response.status_code == 200
    assert "Welcome to flask-k8s Charm" in response.text
    assert get_url_from_relation(juju, "flask-k8s/0") == f"https://{external_hostname}/app1"

    # HTTP with hostname
    juju.config(gateway_api_integrator, {"enforce-https": False})
    juju.wait(
        lambda status: jubilant.all_active(
            status, ingress_configurator, "flask-k8s", gateway_api_integrator
        ),
        timeout=600,
    )

    for additional_hostname in [external_hostname] + additional_hostnames:
        response = requests.get(
            f"https://{gateway_address}/app1",
            verify=False,
            timeout=10,
            headers={"Host": additional_hostname},
        )
        assert response.status_code == 200, (
            f"Failed to route to {additional_hostname}: "
            f"status={response.status_code}"
        )
        assert "Welcome to flask-k8s Charm" in response.text
