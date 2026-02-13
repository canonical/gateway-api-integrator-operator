# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm config."""

from unittest.mock import MagicMock

import pytest
from lightkube.core.client import Client
from lightkube.generic_resource import GenericGlobalResource
from lightkube.models.meta_v1 import ObjectMeta
from ops.testing import Harness

from state.config import CharmConfig, InvalidCharmConfigError

from .conftest import GATEWAY_CLASS_CONFIG


@pytest.mark.parametrize(
    "available_gateway_classes",
    [
        pytest.param(GATEWAY_CLASS_CONFIG, id="available."),
        pytest.param("not-available", id="not available."),
    ],
)
def test_config(harness: Harness, available_gateway_classes: str):
    """
    arrange: Given a charm with unavailable gateway class/invalid config.
    act: Initialize the CharmConfig state component.
    assert: InvalidCharmConfigError is raised in both cases.
    """
    harness.update_config(
        {
            "gateway-class": GATEWAY_CLASS_CONFIG,
        }
    )
    client_mock = MagicMock(spec=Client)
    client_mock.list = MagicMock(
        return_value=[GenericGlobalResource(metadata=ObjectMeta(name=available_gateway_classes))]
    )
    harness.begin()
    with pytest.raises(InvalidCharmConfigError):
        _ = CharmConfig.from_charm(harness.charm, client_mock)


def test_config_enforce_https_with_hostname(harness: Harness):
    """
    arrange: Given a charm with enforce-https enabled and a valid hostname.
    act: Initialize the CharmConfig state component.
    assert: CharmConfig is created successfully with enforce_https=True.
    """
    harness.update_config(
        {
            "gateway-class": GATEWAY_CLASS_CONFIG,
            "external-hostname": "example.com",
            "enforce-https": True,
        }
    )
    client_mock = MagicMock(spec=Client)
    client_mock.list = MagicMock(
        return_value=[GenericGlobalResource(metadata=ObjectMeta(name=GATEWAY_CLASS_CONFIG))]
    )
    harness.begin()

    config = CharmConfig.from_charm(harness.charm, client_mock)

    assert config.gateway_class_name == GATEWAY_CLASS_CONFIG
    assert config.external_hostname == "example.com"
    assert config.enforce_https is True


def test_config_enforce_https_false_without_hostname(harness: Harness):
    """
    arrange: Given a charm with enforce-https disabled and no hostname.
    act: Initialize the CharmConfig state component.
    assert: CharmConfig is created successfully with enforce_https=False and empty hostname.
    """
    harness.update_config(
        {
            "gateway-class": GATEWAY_CLASS_CONFIG,
            "external-hostname": "",
            "enforce-https": False,
        }
    )
    client_mock = MagicMock(spec=Client)
    client_mock.list = MagicMock(
        return_value=[GenericGlobalResource(metadata=ObjectMeta(name=GATEWAY_CLASS_CONFIG))]
    )
    harness.begin()

    config = CharmConfig.from_charm(harness.charm, client_mock)

    assert config.gateway_class_name == GATEWAY_CLASS_CONFIG
    assert config.external_hostname == ""
    assert config.enforce_https is False


def test_config_enforce_https_true_without_hostname(harness: Harness):
    """
    arrange: Given a charm with enforce-https enabled but no hostname.
    act: Initialize the CharmConfig state component.
    assert: InvalidCharmConfigError is raised.
    """
    harness.update_config(
        {
            "gateway-class": GATEWAY_CLASS_CONFIG,
            "external-hostname": "",
            "enforce-https": True,
        }
    )
    client_mock = MagicMock(spec=Client)
    client_mock.list = MagicMock(
        return_value=[GenericGlobalResource(metadata=ObjectMeta(name=GATEWAY_CLASS_CONFIG))]
    )
    harness.begin()

    with pytest.raises(InvalidCharmConfigError, match="external-hostname is required"):
        _ = CharmConfig.from_charm(harness.charm, client_mock)


def test_config_enforce_https_false_with_hostname(harness: Harness):
    """
    arrange: Given a charm with enforce-https disabled and a valid hostname.
    act: Initialize the CharmConfig state component.
    assert: CharmConfig is created successfully with enforce_https=False and hostname set.
    """
    harness.update_config(
        {
            "gateway-class": GATEWAY_CLASS_CONFIG,
            "external-hostname": "example.com",
            "enforce-https": False,
        }
    )
    client_mock = MagicMock(spec=Client)
    client_mock.list = MagicMock(
        return_value=[GenericGlobalResource(metadata=ObjectMeta(name=GATEWAY_CLASS_CONFIG))]
    )
    harness.begin()

    config = CharmConfig.from_charm(harness.charm, client_mock)

    assert config.gateway_class_name == GATEWAY_CLASS_CONFIG
    assert config.external_hostname == "example.com"
    assert config.enforce_https is False


def test_config_invalid_hostname_format(harness: Harness):
    """
    arrange: Given a charm with an invalid hostname format.
    act: Initialize the CharmConfig state component.
    assert: InvalidCharmConfigError is raised.
    """
    harness.update_config(
        {
            "gateway-class": GATEWAY_CLASS_CONFIG,
            "external-hostname": "INVALID_HOSTNAME",
            "enforce-https": False,
        }
    )
    client_mock = MagicMock(spec=Client)
    client_mock.list = MagicMock(
        return_value=[GenericGlobalResource(metadata=ObjectMeta(name=GATEWAY_CLASS_CONFIG))]
    )
    harness.begin()

    with pytest.raises(InvalidCharmConfigError, match="external-hostname must match pattern"):
        _ = CharmConfig.from_charm(harness.charm, client_mock)
