# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

# Disable protected access rules due to the need to test charm._labels
# pylint: disable=protected-access
"""Unit tests for gateway resource."""

from unittest.mock import MagicMock

import ops
import pytest
from httpx import Response
from lightkube.core.client import Client
from lightkube.core.exceptions import ApiError
from lightkube.generic_resource import GenericNamespacedResource
from lightkube.models.meta_v1 import ObjectMeta, Status
from ops.testing import Harness

from resource_manager.gateway import GatewayResourceDefinition, GatewayResourceManager
from state.config import CharmConfig
from state.gateway import GatewayResourceInformation
from state.tls import TLSInformation

from .conftest import GATEWAY_CLASS_CONFIG


@pytest.mark.usefixtures("client_with_mock_external")
def test_create_gateway(  # pylint: disable=too-many-arguments
    harness: Harness,
    certificates_relation_data: dict[str, str],
    gateway_relation_application_data: dict[str, str],
    gateway_relation_unit_data: dict[str, str],
    config: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    """
    arrange: Given a charm with mocked lightkube client, juju secret, relations and gateway ip.
    act: update the charm's config with the correct values.
    assert: the charm goes into active status.
    """
    monkeypatch.setattr(
        "resource_manager.gateway.GatewayResourceManager.current_gateway_resource",
        MagicMock(return_value=None),
    )
    harness.add_relation(
        "gateway",
        "requirer-charm",
        app_data=gateway_relation_application_data,
        unit_data=gateway_relation_unit_data,
    )
    relation_id = harness.add_relation("certificates", "self-signed-certificates")
    harness.update_relation_data(relation_id, harness.model.app.name, certificates_relation_data)
    harness.set_leader()
    harness.begin()

    harness.update_config(config)

    assert harness.charm.unit.status.name == ops.ActiveStatus.name


def test_gateway_resource_definition_insufficient_permission(
    harness: Harness,
    certificates_relation_data: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    config: dict[str, str],
):
    """
    arrange: given a charm with mocked lightkube client that returns 403.
    act: when agent reconciliation triggers.
    assert: The exception is handled and charm is set to blocked state.
    """
    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    monkeypatch.setattr(
        "lightkube.models.meta_v1.Status.from_dict", MagicMock(return_value=Status(code=403))
    )
    lightkube_client_mock = MagicMock(spec=Client)
    lightkube_client_mock.return_value.list = MagicMock(
        side_effect=ApiError(response=MagicMock(spec=Response))
    )
    monkeypatch.setattr(
        "charm._get_client",
        lightkube_client_mock,
    )
    harness.begin()
    harness.update_config(config)

    assert harness.charm.unit.status.name == ops.BlockedStatus.name


def test_gateway_resource_definition_api_error_4xx(
    harness: Harness,
    certificates_relation_data: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    config: dict[str, str],
):
    """
    arrange: given a charm with mocked lightkube client that returns 404.
    act: when agent reconciliation triggers.
    assert: Exception is re-raised.
    """
    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    monkeypatch.setattr(
        "lightkube.models.meta_v1.Status.from_dict", MagicMock(return_value=Status(code=404))
    )
    lightkube_client_mock = MagicMock(spec=Client)
    lightkube_client_mock.return_value.list = MagicMock(
        side_effect=ApiError(response=MagicMock(spec=Response))
    )
    monkeypatch.setattr(
        "charm._get_client",
        lightkube_client_mock,
    )
    harness.begin()

    with pytest.raises(ApiError):
        harness.update_config(config)


def test_gateway_gen_resource(
    harness: Harness,
    config: dict[str, str],
    certificates_relation_data: dict[str, str],
    client_with_mock_external: MagicMock,
):
    """
    arrange: Given a charm with valid config and mocked client.
    act: Call _gen_resource from the required state components.
    assert: The k8s resource is correctly generated.
    """
    relation_id = harness.add_relation("certificates", "self-signed-certificates")
    harness.update_relation_data(relation_id, harness.model.app.name, certificates_relation_data)
    harness.update_config(config)
    harness.begin()

    gateway_resource_information = GatewayResourceInformation.from_charm(harness.charm)
    gateway_resource_manager = GatewayResourceManager(
        labels=harness.charm._labels,
        client=client_with_mock_external,
    )
    tls_information = TLSInformation.from_charm(harness.charm, harness.charm.certificates)
    config = CharmConfig.from_charm(harness.charm, client_with_mock_external)
    gateway_resource = gateway_resource_manager._gen_resource(
        GatewayResourceDefinition(gateway_resource_information, config, tls_information)
    )

    assert gateway_resource.spec["gatewayClassName"] == GATEWAY_CLASS_CONFIG
    assert len(gateway_resource.spec["listeners"])

    
def test_get_current_gateway_no_resource(mock_lightkube_client: MagicMock):
    """
    arrange: Given an GatewayResourceManager with mocked lightkube client
    list method returning an empty list.
    act: Call current_gateway_resource.
    assert: The method returns None.
    """
    mock_lightkube_client.list = MagicMock(return_value=[])
    gateway_resource_manager = GatewayResourceManager(
        labels={},
        client=mock_lightkube_client,
    )
    assert gateway_resource_manager.current_gateway_resource() is None


def test_get_current_gateway(mock_lightkube_client: MagicMock):
    """
    arrange: Given an GatewayResourceManager with mocked lightkube client
    list method returning an a list of one gateway resource.
    act: Call current_gateway_resource.
    assert: The method returns the correct gateway resource.
    """
    mock_lightkube_client.list = MagicMock(
        return_value=[GenericNamespacedResource(metadata=ObjectMeta(name="gateway"))]
    )
    gateway_resource_manager = GatewayResourceManager(
        labels={},
        client=mock_lightkube_client,
    )
    gateway = gateway_resource_manager.current_gateway_resource()
    assert gateway.metadata.name == "gateway"


def test_gateway_address(mock_lightkube_client: MagicMock):
    """
    arrange: Given an GatewayResourceManager with mocked lightkube client
    returning a gateway with 10.0.0.0 as LB ip address.
    act: Call gateway_address.
    assert: The return value of the called method is the LB ip address.
    """
    mock_lightkube_client.get = MagicMock(
        return_value=GenericNamespacedResource(status={"addresses": [{"value": "10.0.0.0"}]})
    )
    gateway_resource_manager = GatewayResourceManager(
        labels={},
        client=mock_lightkube_client,
    )
    assert gateway_resource_manager.gateway_address(name="") == "10.0.0.0"


def test_gateway_address_not_available(
    mock_lightkube_client: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    """
    arrange: Given an GatewayResourceManager with mocked lightkube client
    returning a gateway with no LB ip available.
    act: Call gateway_address.
    assert: The return value of the called method is None.
    """
    monkeypatch.setattr("time.time", MagicMock(side_effect=[0, 5, 61, 62]))
    monkeypatch.setattr("time.sleep", MagicMock())

    mock_lightkube_client.get = MagicMock(
        return_value=GenericNamespacedResource(status={"addresses": []})
    )
    gateway_resource_manager = GatewayResourceManager(
        labels={},
        client=mock_lightkube_client,
    )
    assert gateway_resource_manager.gateway_address(name="") is None
