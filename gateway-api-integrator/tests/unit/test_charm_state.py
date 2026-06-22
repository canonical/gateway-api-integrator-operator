# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm config."""

import pytest
from pydantic import ValidationError

from state.charm_state import (
    CharmState,
    ProxyMode,
)


def test_valid_ingress_config():
    """
    arrange: Provide valid values for ingress fields.
    act: Instantiate CharmState for ingress mode.
    assert: All fields are correctly set.
    """
    charm_state = CharmState(
        gateway_class_name="cilium",
        enforce_https=True,
        proxy_mode=ProxyMode.INGRESS,
        requires_ip_certificate=False,
        hostnames={"gateway.internal"},
    )
    assert charm_state.hostnames == {"gateway.internal"}
    assert charm_state.proxy_mode == ProxyMode.INGRESS
    assert charm_state.gateway_class_name == "cilium"
    assert charm_state.enforce_https is True


def test_valid_ingress_config_no_hostnames():
    """
    arrange: Provide no ingress hostnames.
    act: Instantiate CharmState for ingress mode.
    assert: hostnames is empty and other fields are correctly set.
    """
    charm_state = CharmState(
        gateway_class_name="cilium",
        enforce_https=False,
        proxy_mode=ProxyMode.INGRESS,
        requires_ip_certificate=False,
        hostnames=set(),
    )
    assert charm_state.hostnames == set()
    assert charm_state.enforce_https is False


def test_valid_gateway_route_config_enforce_https_false():
    """
    arrange: Provide enforce_https as False.
    act: Instantiate CharmState for gateway-route mode.
    assert: enforce_https is correctly set to False.
    """
    charm_state = CharmState(
        gateway_class_name="cilium",
        enforce_https=False,
        proxy_mode=ProxyMode.GATEWAY_ROUTE,
        requires_ip_certificate=False,
        hostnames={"example.com"},
    )
    assert charm_state.hostnames == {"example.com"}
    assert charm_state.enforce_https is False


def test_valid_inactive_config():
    """The base charm state represents the inactive/default mode."""
    charm_state = CharmState(
        gateway_class_name="cilium",
        enforce_https=False,
        proxy_mode=ProxyMode.INACTIVE,
        requires_ip_certificate=False,
        hostnames=set(),
    )
    assert type(charm_state) is CharmState


def test_invalid_gateway_class_name_empty():
    """
    arrange: Provide an empty string as gateway_class_name.
    act: Instantiate CharmState.
    assert: ValidationError is raised due to min_length=1 constraint.
    """
    with pytest.raises(ValidationError):
        CharmState(
            gateway_class_name="",
            enforce_https=True,
            proxy_mode=ProxyMode.INGRESS,
            requires_ip_certificate=False,
            hostnames={"gateway.internal"},
        )


def test_invalid_ingress_hostname():
    """
    arrange: Provide an invalid hostname string (not a valid FQDN).
    act: Instantiate CharmState for ingress mode.
    assert: ValidationError is raised by the valid_fqdn BeforeValidator.
    """
    with pytest.raises(ValidationError):
        CharmState(
            gateway_class_name="cilium",
            enforce_https=True,
            proxy_mode=ProxyMode.INGRESS,
            requires_ip_certificate=False,
            hostnames={"not a valid hostname!"},
        )


def test_invalid_gateway_route_hostname():
    """Gateway-route state should validate each hostname as a FQDN."""
    with pytest.raises(ValidationError):
        CharmState(
            gateway_class_name="cilium",
            enforce_https=True,
            proxy_mode=ProxyMode.GATEWAY_ROUTE,
            requires_ip_certificate=False,
            hostnames={"not a valid hostname!"},
        )


def test_invalid_ingress_multiple_hostnames():
    """Ingress mode should reject multiple hostnames."""
    with pytest.raises(ValidationError):
        CharmState(
            gateway_class_name="cilium",
            enforce_https=True,
            proxy_mode=ProxyMode.INGRESS,
            requires_ip_certificate=False,
            hostnames={"one.example.com", "two.example.com"},
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
    act: Instantiate CharmState for ingress mode.
    assert: hostnames is correctly set without validation errors.
    """
    charm_state = CharmState(
        gateway_class_name="cilium",
        enforce_https=True,
        proxy_mode=ProxyMode.INGRESS,
        requires_ip_certificate=False,
        hostnames={hostname},
    )
    assert charm_state.hostnames == {hostname}
