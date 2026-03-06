# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm config."""

import pytest
from pydantic import ValidationError

from state.config import CharmConfig, ProxyMode


def test_valid_config():
    """
    arrange: Provide valid values for all CharmConfig fields.
    act: Instantiate CharmConfig.
    assert: All fields are correctly set.
    """
    config = CharmConfig(
        hostname="gateway.internal",
        gateway_class_name="cilium",
        enforce_https=True,
        proxy_mode=ProxyMode.INGRESS,
    )
    assert config.hostname == "gateway.internal"
    assert config.gateway_class_name == "cilium"
    assert config.enforce_https is True
    assert config.proxy_mode == ProxyMode.INGRESS


def test_valid_config_hostname_none():
    """
    arrange: Provide None as hostname.
    act: Instantiate CharmConfig.
    assert: hostname is None and other fields are correctly set.
    """
    config = CharmConfig(
        hostname=None,
        gateway_class_name="cilium",
        enforce_https=False,
        proxy_mode=ProxyMode.INACTIVE,
    )
    assert config.hostname is None
    assert config.enforce_https is False
    assert config.proxy_mode == ProxyMode.INACTIVE


def test_valid_config_enforce_https_false():
    """
    arrange: Provide enforce_https as False.
    act: Instantiate CharmConfig.
    assert: enforce_https is correctly set to False.
    """
    config = CharmConfig(
        hostname="example.com",
        gateway_class_name="cilium",
        enforce_https=False,
        proxy_mode=ProxyMode.GATEWAY_ROUTE,
    )
    assert config.enforce_https is False
    assert config.proxy_mode == ProxyMode.GATEWAY_ROUTE


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
    act: Instantiate CharmConfig.
    assert: proxy_mode is correctly set.
    """
    config = CharmConfig(
        hostname="gateway.internal",
        gateway_class_name="cilium",
        enforce_https=True,
        proxy_mode=proxy_mode,
    )
    assert config.proxy_mode == proxy_mode


def test_invalid_gateway_class_name_empty():
    """
    arrange: Provide an empty string as gateway_class_name.
    act: Instantiate CharmConfig.
    assert: ValidationError is raised due to min_length=1 constraint.
    """
    with pytest.raises(ValidationError):
        CharmConfig(
            hostname="gateway.internal",
            gateway_class_name="",
            enforce_https=True,
            proxy_mode=ProxyMode.INGRESS,
        )


def test_invalid_hostname():
    """
    arrange: Provide an invalid hostname string (not a valid FQDN).
    act: Instantiate CharmConfig.
    assert: ValidationError is raised by the valid_fqdn BeforeValidator.
    """
    with pytest.raises(ValidationError):
        CharmConfig(
            hostname="not a valid hostname!",
            gateway_class_name="cilium",
            enforce_https=True,
            proxy_mode=ProxyMode.INGRESS,
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
    act: Instantiate CharmConfig.
    assert: hostname is correctly set without validation errors.
    """
    config = CharmConfig(
        hostname=hostname,
        gateway_class_name="cilium",
        enforce_https=True,
        proxy_mode=ProxyMode.INGRESS,
    )
    assert config.hostname == hostname
