# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm config."""

import pytest
from pydantic import ValidationError

from state.charm_state import (
    CharmState,
    GatewayRouteCharmState,
    IngressCharmState,
)


def test_valid_ingress_config():
    """
    arrange: Provide valid values for ingress fields.
    act: Instantiate IngressCharmState.
    assert: All fields are correctly set.
    """
    charm_state = IngressCharmState(
        gateway_class_name="cilium",
        enforce_https=True,
        requires_ip_certificate=False,
        hostname="gateway.internal",
    )
    assert charm_state.hostname == "gateway.internal"
    assert charm_state.gateway_class_name == "cilium"
    assert charm_state.enforce_https is True


def test_valid_ingress_config_hostname_none():
    """
    arrange: Provide None as ingress hostname.
    act: Instantiate IngressCharmState.
    assert: hostname is None and other fields are correctly set.
    """
    charm_state = IngressCharmState(
        gateway_class_name="cilium",
        enforce_https=False,
        requires_ip_certificate=False,
        hostname=None,
    )
    assert charm_state.hostname is None
    assert charm_state.enforce_https is False


def test_valid_gateway_route_config_enforce_https_false():
    """
    arrange: Provide enforce_https as False.
    act: Instantiate GatewayRouteCharmState.
    assert: enforce_https is correctly set to False.
    """
    charm_state = GatewayRouteCharmState(
        hostnames={"example.com"},
        gateway_class_name="cilium",
        enforce_https=False,
        requires_ip_certificate=False,
    )
    assert charm_state.hostnames == {"example.com"}
    assert charm_state.enforce_https is False


def test_valid_inactive_config():
    """The base charm state represents the inactive/default mode."""
    charm_state = CharmState(
        gateway_class_name="cilium",
        enforce_https=False,
        requires_ip_certificate=False,
    )
    assert type(charm_state) is CharmState


def test_invalid_gateway_class_name_empty():
    """
    arrange: Provide an empty string as gateway_class_name.
    act: Instantiate CharmState.
    assert: ValidationError is raised due to min_length=1 constraint.
    """
    with pytest.raises(ValidationError):
        IngressCharmState(
            gateway_class_name="",
            enforce_https=True,
            requires_ip_certificate=False,
            hostname="gateway.internal",
        )


def test_invalid_ingress_hostname():
    """
    arrange: Provide an invalid hostname string (not a valid FQDN).
    act: Instantiate IngressCharmState.
    assert: ValidationError is raised by the valid_fqdn BeforeValidator.
    """
    with pytest.raises(ValidationError):
        IngressCharmState(
            gateway_class_name="cilium",
            enforce_https=True,
            requires_ip_certificate=False,
            hostname="not a valid hostname!",
        )


def test_invalid_gateway_route_hostname():
    """Gateway-route state should validate each hostname as a FQDN."""
    with pytest.raises(ValidationError):
        GatewayRouteCharmState(
            hostnames={"not a valid hostname!"},
            gateway_class_name="cilium",
            enforce_https=True,
            requires_ip_certificate=False,
        )


@pytest.mark.parametrize(
    "hostname",
    [
        pytest.param("gateway.internal", id="subdomain"),
        pytest.param("my.gateway.example.com", id="multi-level"),
        pytest.param("example.com", id="simple-domain"),
    ],
)
def test_valid_hostnames(hostname: str):
    """
    arrange: Provide various valid FQDN hostnames.
    act: Instantiate IngressCharmState.
    assert: hostname is correctly set without validation errors.
    """
    charm_state = IngressCharmState(
        gateway_class_name="cilium",
        enforce_https=True,
        requires_ip_certificate=False,
        hostname=hostname,
    )
    assert charm_state.hostname == hostname
