# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm config."""

import pytest
from pydantic import ValidationError

from state.charm_state import CharmState, ProxyMode


def test_valid_config():
    """
    arrange: Provide valid values for all CharmState fields.
    act: Instantiate CharmState.
    assert: All fields are correctly set.
    """
    config = CharmState(
        hostnames={"gateway.internal"},
        gateway_class_name="cilium",
        enforce_https=True,
        proxy_mode=ProxyMode.INGRESS,
        requires_ip_certificate=False,
    )
    assert config.hostnames == {"gateway.internal"}
    assert config.hostname == "gateway.internal"
    assert config.gateway_class_name == "cilium"
    assert config.enforce_https is True
    assert config.proxy_mode == ProxyMode.INGRESS


def test_valid_config_hostname_none():
    """
    arrange: Provide None as hostname.
    act: Instantiate CharmState.
    assert: hostname is None and other fields are correctly set.
    """
    config = CharmState(
        hostnames=set(),
        gateway_class_name="cilium",
        enforce_https=False,
        proxy_mode=ProxyMode.INGRESS,
        requires_ip_certificate=False,
    )
    assert config.hostnames == set()
    assert config.hostname is None
    assert config.enforce_https is False
    assert config.proxy_mode == ProxyMode.INGRESS


def test_valid_config_enforce_https_false():
    """
    arrange: Provide enforce_https as False.
    act: Instantiate CharmState.
    assert: enforce_https is correctly set to False.
    """
    config = CharmState(
        hostnames={"example.com"},
        gateway_class_name="cilium",
        enforce_https=False,
        proxy_mode=ProxyMode.GATEWAY_ROUTE,
        requires_ip_certificate=False,
    )
    assert config.enforce_https is False
    assert config.proxy_mode == ProxyMode.GATEWAY_ROUTE


def test_hostname_property_raises_for_multiple_hostnames():
    """Hostname property should fail when multiple hostnames are configured."""
    config = CharmState(
        hostnames={"a.example.com", "b.example.com"},
        gateway_class_name="cilium",
        enforce_https=False,
        proxy_mode=ProxyMode.GATEWAY_ROUTE,
        requires_ip_certificate=False,
    )

    with pytest.raises(ValueError):
        _ = config.hostname


def test_hostname_property_raises_outside_ingress_mode():
    """Hostname property should fail when proxy mode is not ingress."""
    config = CharmState(
        hostnames={"example.com"},
        gateway_class_name="cilium",
        enforce_https=False,
        proxy_mode=ProxyMode.GATEWAY_ROUTE,
        requires_ip_certificate=False,
    )
    with pytest.raises(ValueError):
        _ = config.hostname


@pytest.mark.parametrize(
    "proxy_mode",
    [
        pytest.param(ProxyMode.INGRESS, id="ingress"),
        pytest.param(ProxyMode.GATEWAY_ROUTE, id="gateway-route"),
        pytest.param(ProxyMode.INACTIVE, id="inactive"),
    ],
)
def test_valid_proxy_modes(proxy_mode: ProxyMode):
    """
    arrange: Provide each valid ProxyMode value.
    act: Instantiate CharmState.
    assert: proxy_mode is correctly set.
    """
    config = CharmState(
        hostnames={"gateway.internal"},
        gateway_class_name="cilium",
        enforce_https=True,
        proxy_mode=proxy_mode,
        requires_ip_certificate=False,
    )
    assert config.proxy_mode == proxy_mode


def test_invalid_gateway_class_name_empty():
    """
    arrange: Provide an empty string as gateway_class_name.
    act: Instantiate CharmState.
    assert: ValidationError is raised due to min_length=1 constraint.
    """
    with pytest.raises(ValidationError):
        CharmState(
            hostnames={"gateway.internal"},
            gateway_class_name="",
            enforce_https=True,
            proxy_mode=ProxyMode.INGRESS,
            requires_ip_certificate=False,
        )


def test_invalid_hostname():
    """
    arrange: Provide an invalid hostname string (not a valid FQDN).
    act: Instantiate CharmState.
    assert: ValidationError is raised by the valid_fqdn BeforeValidator.
    """
    with pytest.raises(ValidationError):
        CharmState(
            hostnames={"not a valid hostname!"},
            gateway_class_name="cilium",
            enforce_https=True,
            proxy_mode=ProxyMode.INGRESS,
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
    act: Instantiate CharmState.
    assert: hostname is correctly set without validation errors.
    """
    config = CharmState(
        hostnames={hostname},
        gateway_class_name="cilium",
        enforce_https=True,
        proxy_mode=ProxyMode.INGRESS,
        requires_ip_certificate=False,
    )
    assert config.hostnames == {hostname}
