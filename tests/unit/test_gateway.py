# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for gateway resource."""

import typing
from typing import Dict
from unittest.mock import MagicMock

import ops
import pytest
from ops.testing import Harness

import resource_manager
import resource_manager.gateway
import resource_manager.resource_manager
from state.config import CharmConfig
from state.gateway import GatewayResourceDefinition
from state.secret import SecretResourceDefinition
from tls_relation import TLSRelationService

from .conftest import GATEWAY_CLASS_CONFIG, TEST_EXTERNAL_HOSTNAME_CONFIG


@pytest.mark.usefixtures("patch_lightkube_client")
@pytest.mark.parametrize(
    "gateway_address",
    [
        pytest.param("10.0.0.0", id="LB address available."),
        pytest.param(
            None,
            id="LB address not available.",
        ),
    ],
)
def test_gateway_resource_definition(
    harness: Harness,
    certificates_relation_data: Dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    gateway_address: typing.Optional[str],
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
        "state.config.CharmConfig.from_charm", MagicMock(return_value=MagicMock(spec=CharmConfig))
    )
    monkeypatch.setattr(
        "resource_manager.gateway.GatewayResourceManager.gateway_address",
        MagicMock(return_value=gateway_address),
    )
    monkeypatch.setattr(
        "resource_manager.secret.SecretResourceManager",
        MagicMock(),
    )
    monkeypatch.setattr(
        "resource_manager.secret.SecretResourceManager",
        MagicMock(),
    )

    harness.update_config(
        {"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG, "gateway-class": GATEWAY_CLASS_CONFIG}
    )

    if not gateway_address:
        assert harness.charm.unit.status.name == ops.WaitingStatus.name

    gateway_resource_definition = GatewayResourceDefinition.from_charm(harness.charm)
    secret_resource_definition = SecretResourceDefinition.from_charm(harness.charm)
    define_resource_mock.assert_called_once_with(
        gateway_resource_definition, config, secret_resource_definition
    )


@pytest.mark.usefixtures("patch_lightkube_client")
@pytest.mark.parametrize(
    "exc",
    [
        pytest.param(
            resource_manager.gateway.CreateGatewayError, id="Error creating gateway(k8s api)"
        ),
        pytest.param(
            resource_manager.resource_manager.InvalidResourceError,
            id="Invalid resource definition error.",
        ),
    ],
)
def test_gateway_resource_definition_create_gateway_error(
    harness: Harness,
    certificates_relation_data: Dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    exc: Exception,
):
    """
    arrange: given a charm with mocked lightkube client and resource manager
    that raises CreateGatewayError and InvalidResourceError.
    act: when agent reconciliation triggers.
    assert: the gateway resource is created with the expected values.
    """
    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    harness.begin()
    monkeypatch.setattr("charm.TLSRelationService", MagicMock(spec=TLSRelationService))

    monkeypatch.setattr(
        "resource_manager.gateway.GatewayResourceManager.define_resource",
        MagicMock(side_effect=exc("Error message.")),
    )
    with pytest.raises(RuntimeError):
        harness.update_config(
            {
                "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
                "gateway-class": GATEWAY_CLASS_CONFIG,
            }
        )


@pytest.mark.usefixtures("patch_lightkube_client")
def test_gateway_resource_definition_insufficient_permission(
    harness: Harness,
    certificates_relation_data: Dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    """
    arrange: given a charm with mocked lightkube client and resource manager
    that raises InsufficientPermissionError.
    act: when agent reconciliation triggers.
    assert: the gateway resource is created with the expected values.
    """
    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    harness.begin()
    monkeypatch.setattr("charm.TLSRelationService", MagicMock(spec=TLSRelationService))

    monkeypatch.setattr(
        "resource_manager.gateway.GatewayResourceManager.define_resource",
        MagicMock(
            side_effect=resource_manager.resource_manager.InsufficientPermissionError(
                "Error message."
            )
        ),
    )

    harness.update_config(
        {
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        }
    )

    assert harness.charm.unit.status.name == ops.BlockedStatus.name
