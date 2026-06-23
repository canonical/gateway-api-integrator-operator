# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for testing gateway-api with ingress-configurator."""

import jubilant
import pytest
import requests
from .helper import (
    assert_gateway_route_response,
    get_gateway_ip,
)


def test_enforced_mode(
    juju: jubilant.Juju,
    ingress_configurator: str,
    gateway_api_integrator: str,
    gateway_route_backend_application: str,
    external_hostname: str,
):
    """Test gateway-route with enforce-https=True (default) and TLS present.

    Assert that:
    - HTTPS traffic is routed correctly to the backend.
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

    gateway_address = get_gateway_ip(juju, gateway_api_integrator)

    assert_gateway_route_response(
        gateway_address,
        external_hostname,
        "/app1/",
        body_contains="Hello from any_charm",
    )

    # HTTP should redirect to HTTPS
    assert_gateway_route_response(
        gateway_address,
        external_hostname,
        "/app1/",
        scheme="http",
        expected_status=301,
    )


def test_enabled_mode(
    juju: jubilant.Juju,
    ingress_configurator: str,
    gateway_api_integrator: str,
    gateway_route_backend_application: str,
    external_hostname: str,
):
    """Test gateway-route with enforce-https=False and TLS present.

    Assert that:
    - Both HTTP and HTTPS traffic are routed correctly to the backend.
    """
    juju.config(gateway_api_integrator, {"enforce-https": False})
    juju.wait(
        lambda status: jubilant.all_active(
            status, ingress_configurator, gateway_route_backend_application, gateway_api_integrator
        ),
        timeout=600,
    )

    gateway_address = get_gateway_ip(juju, gateway_api_integrator)

    # HTTPS should work
    assert_gateway_route_response(
        gateway_address,
        external_hostname,
        "/app1/",
        scheme="https",
        body_contains="Hello from any_charm",
    )

    # HTTP should also work (no redirect)
    assert_gateway_route_response(
        gateway_address,
        external_hostname,
        "/app1/",
        scheme="http",
        body_contains="Hello from any_charm",
    )


def test_disabled_mode(
    juju: jubilant.Juju,
    ingress_configurator: str,
    gateway_api_integrator: str,
    gateway_route_backend_application: str,
    external_hostname: str,
):
    """Test gateway-route with enforce-https=False and TLS removed.

    Assert that:
    - HTTP traffic is routed correctly to the backend.
    - HTTPS is not available.
    """
    juju.remove_relation(gateway_api_integrator, "self-signed-certificates")
    juju.wait(
        lambda status: jubilant.all_active(
            status, ingress_configurator, gateway_route_backend_application, gateway_api_integrator
        ),
        timeout=600,
    )

    gateway_address = get_gateway_ip(juju, gateway_api_integrator)

    # HTTP should work
    assert_gateway_route_response(
        gateway_address,
        external_hostname,
        "/app1/",
        scheme="http",
        body_contains="Hello from any_charm",
    )

    # HTTPS should not be available
    with pytest.raises(requests.exceptions.ConnectionError):
        requests.get(
            f"https://{gateway_address}/app1/",
            headers={"Host": external_hostname},
            verify=False,  # nosec
            timeout=10,
        )


def test_disabled_mode_without_hostname(
    juju: jubilant.Juju,
    ingress_configurator: str,
    gateway_api_integrator: str,
    gateway_route_backend_application: str,
):
    """Test gateway-route with enforce-https=False, TLS removed, and no hostname configured.

    Assert that:
    - HTTP traffic is routed correctly to the backend by IP.
    """
    juju.remove_relation(gateway_api_integrator, "self-signed-certificates")
    juju.config(ingress_configurator, reset="hostname")
    juju.wait(
        lambda status: jubilant.all_active(
            status, ingress_configurator, gateway_route_backend_application, gateway_api_integrator
        ),
        timeout=600,
    )

    gateway_address = get_gateway_ip(juju, gateway_api_integrator)

    assert_gateway_route_response(
        gateway_address,
        None,
        "/app1/",
        scheme="http",
        body_contains="Hello from any_charm",
    )
