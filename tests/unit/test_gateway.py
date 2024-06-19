# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for gateway resource."""

from typing import Dict
from unittest.mock import MagicMock

import pytest
from ops.testing import Harness

from state.config import CharmConfig
from state.gateway import GatewayResourceDefinition
from state.secret import SecretResourceDefinition
from tls_relation import TLSRelationService

from .conftest import GATEWAY_CLASS_CONFIG, TEST_EXTERNAL_HOSTNAME_CONFIG


@pytest.mark.usefixtures("patch_lightkube_client")
def test_gateway_resource_definition(
    harness: Harness, certificates_relation_data: Dict[str, str], monkeypatch: pytest.MonkeyPatch
):
    """
    arrange: given a charm with mocked lightkube client and resource manager.
    act: when agent reconciliation triggers.
    assert: the gateway resource is created with the expected values.
    """
    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    harness.begin()
    monkeypatch.setattr("charm.TLSRelationService", MagicMock(spec=TLSRelationService))
    define_resource_mock = MagicMock()
    monkeypatch.setattr(
        "resource_manager.gateway.GatewayResourceManager.define_resource", define_resource_mock
    )
    monkeypatch.setattr(
        "resource_manager.gateway.GatewayResourceManager.gateway_address",
        MagicMock(return_value=TEST_EXTERNAL_HOSTNAME_CONFIG),
    )
    monkeypatch.setattr(
        "resource_manager.secret.SecretResourceManager",
        MagicMock(),
    )

    harness.update_config(
        {"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG, "gateway-class": GATEWAY_CLASS_CONFIG}
    )

    config = CharmConfig.from_charm(harness.charm)
    gateway_resource_definition = GatewayResourceDefinition.from_charm(harness.charm)
    secret_resource_definition = SecretResourceDefinition.from_charm(harness.charm)
    assert config.external_hostname == TEST_EXTERNAL_HOSTNAME_CONFIG
    assert config.gateway_class == "cilium"
    define_resource_mock.assert_called_once_with(
        gateway_resource_definition, config, secret_resource_definition
    )
