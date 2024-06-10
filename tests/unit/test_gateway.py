# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for gateway resource."""

from typing import Dict
from unittest.mock import MagicMock

import pytest
from ops.testing import Harness

from tls_relation import TLSRelationService
from resource_definition import GatewayResourceDefinition


@pytest.mark.usefixtures("patch_lightkube_client")
def test_gateway_resource_definition(
    harness: Harness, certificates_relation_data: Dict[str, str], monkeypatch: pytest.MonkeyPatch
):
    """
    arrange: given a charm with mocked lightkube client and resource manager.
    act: when agent reconciliation triggers.
    assert: the gateway resource is created with the expected values.
    """
    hostname = "gateway.internal"
    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    harness.begin()
    monkeypatch.setattr("charm.TLSRelationService", MagicMock(spec=TLSRelationService))
    define_resource_mock = MagicMock()
    monkeypatch.setattr(
        "resource_manager.gateway.GatewayResourceManager.define_resource", define_resource_mock
    )

    harness.update_config({"external-hostname": hostname, "gateway-class": "cilium"})

    gateway_resource_definition = GatewayResourceDefinition.from_charm(harness.charm)
    assert gateway_resource_definition.namespace == harness.model.name
    assert gateway_resource_definition.config.external_hostname == hostname
    assert gateway_resource_definition.config.gateway_class == "cilium"
    define_resource_mock.assert_called_once_with(gateway_resource_definition)
