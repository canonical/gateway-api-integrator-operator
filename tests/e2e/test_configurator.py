# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for testing both charms."""

import socket

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
    unit_data = yaml.load(juju.cli("show-unit", unit_name), Loader=yaml.CLoader)                                                                                                              
                                                                                                                                                                                              
    for relation in unit_data[unit_name]["relation-info"]:                                                                                                                                    
        if relation["endpoint"] == "ingress":                                                                                                                                                 
            # app data is encoded as a string so we have to load it as yaml again :(                                                                                                          
            return yaml.load(relation["application-data"]["ingress"], Loader=yaml.CLoader)["url"]                                                                                             
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


def test_configurator(
    juju: jubilant.Juju,
    gateway_route_configurator: App,
    gateway_api_integrator: App,
    external_hostname: str,
):
    """
    Test that the charms correctly set up the gateway route relation.
    Deploy gateway-route-configurator and integrate it on gateway-route relation.
    Assert that a request to the external hostname is correctly routed to the flask-k8s app
    """
    juju.deploy(
        "flask-k8s",
        channel="latest/edge",
    )

    juju.integrate(
        f"{gateway_route_configurator.name}:ingress",
        "flask-k8s:ingress",
    )
    juju.integrate(
        f"{gateway_api_integrator.name}:gateway-route",
        f"{gateway_route_configurator.name}:gateway-route",
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, gateway_route_configurator.name, "flask-k8s", gateway_api_integrator.name
        ),
        timeout=600,
    )

    # send a request to verify routing
    ip = get_gateway_ip(juju, gateway_api_integrator)
    original_getaddrinfo = socket.getaddrinfo

    def patched_getaddrinfo(
        host, port, family=0, type=0, proto=0, flags=0
    ):  # pylint: disable=too-many-positional-arguments, too-many-arguments, redefined-builtin
        """If the request is for our target hostname, force it to the target IP.
        Otherwise, let it act normally.

        Args:
            host: The hostname being resolved.
            port: The port number.
            family: The address family.
            type: The socket type.
            proto: The protocol.
            flags: Additional flags.

        Returns:
            The address info tuple.
        """  # noqa: D205
        if host == external_hostname:
            return original_getaddrinfo(ip, port, family, type, proto, flags)

        return original_getaddrinfo(host, port, family, type, proto, flags)

    # Apply the patch to the socket library
    socket.getaddrinfo = patched_getaddrinfo

    # --- THE REQUEST ---
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    url = f"https://{external_hostname}/app1"

    response = requests.get(url, verify=False, timeout=10)  # nosec
    assert response.status_code == 200
    assert "Welcome to flask-k8s Charm" in response.text
    assert get_url_from_relation(juju, "flask-k8s/0") == url
