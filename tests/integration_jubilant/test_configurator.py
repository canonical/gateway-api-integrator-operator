import socket

import jubilant
import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning

from .conftest import App

# Disable SSL warnings when using verify=False
urllib3.disable_warnings(InsecureRequestWarning)

def get_gateway_ip(juju, gateway_api_integrator) -> str:
    status = juju.status()
    app_status = status.apps[gateway_api_integrator.name]
    message = app_status.app_status.message
    if "gateway address" in message.lower():
        # Extract IP from message
        parts = message.split(":")
        ip = parts[1].strip()
        return ip

def test_configurator(juju: jubilant.Juju, gateway_route_configurator: App, gateway_api_integrator: App, external_hostname: str):
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

    def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        """If the request is for our target hostname, force it to the target IP.
        Otherwise, let it act normally.
        """  # noqa: D205
        if host == external_hostname:
            return original_getaddrinfo(ip, port, family, type, proto, flags)

        return original_getaddrinfo(host, port, family, type, proto, flags)

    # Apply the patch to the socket library
    socket.getaddrinfo = patched_getaddrinfo

    # --- THE REQUEST ---
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    url = f"https://{external_hostname}/app1"

    response = requests.get(url, verify=False)
    assert response.status_code == 200
    assert "Welcome to flask-k8s Charm" in response.text
