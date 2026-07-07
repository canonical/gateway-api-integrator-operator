# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for testing gateway-api with ingress-configurator."""

import time

import jubilant
import pytest
import requests

from .helper import (
    assert_gateway_route_response,
    get_gateway_ip,
)

# After a mutating juju operation (config change, relation removal) the apps are still
# reported as active/idle from the previous step. juju.wait() can therefore satisfy its
# ready condition against this stale state before the config-changed hook has fired,
# racing ahead of the actual reconcile. A short settle delay lets the hook start (moving
# an agent out of idle) so the subsequent wait observes the real reconvergence cycle.
SETTLE_DELAY = 15


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
        )
        and jubilant.all_agents_idle(
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
        allow_redirects=False,
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
    time.sleep(SETTLE_DELAY)
    juju.wait(
        lambda status: jubilant.all_active(
            status, ingress_configurator, gateway_route_backend_application, gateway_api_integrator
        )
        and jubilant.all_agents_idle(
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
    time.sleep(SETTLE_DELAY)
    juju.wait(
        lambda status: jubilant.all_active(
            status, ingress_configurator, gateway_route_backend_application, gateway_api_integrator
        )
        and jubilant.all_agents_idle(
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
    juju.config(ingress_configurator, reset="hostname")
    time.sleep(SETTLE_DELAY)
    juju.wait(
        lambda status: jubilant.all_active(
            status, ingress_configurator, gateway_route_backend_application, gateway_api_integrator
        )
        and jubilant.all_agents_idle(
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
