# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for gateway resource."""

from unittest.mock import MagicMock, PropertyMock

import ops
import pytest
from lightkube.generic_resource import GenericGlobalResource, GenericNamespacedResource
from ops.model import Secret
from ops.testing import Harness

import resource_manager
import resource_manager.decorator
import resource_manager.gateway
import resource_manager.resource_manager
from state.config import CharmConfig
from state.gateway import GatewayResourceDefinition
from state.secret import SecretResourceDefinition
from tls_relation import TLSRelationService
from resource_manager.gateway import GatewayResourceManager
from .conftest import GATEWAY_CLASS_CONFIG, TEST_EXTERNAL_HOSTNAME_CONFIG
from lightkube.core.exceptions import ApiError
from lightkube.models.meta_v1 import Status
from httpx import Response
from lightkube.core.client import Client
import logging

from lightkube.generic_resource import GenericGlobalResource, GenericNamespacedResource
from lightkube.models.meta_v1 import ObjectMeta

logger = logging.getLogger()


def test_create_gateway(  # pylint: disable=too-many-arguments
    harness: Harness,
    mock_lightkube_client: MagicMock,
    gateway_class_resource: GenericGlobalResource,
    certificates_relation_data: dict[str, str],
    private_key_and_password: tuple[str, str],
    gateway_relation_application_data: dict[str, str],
    gateway_relation_unit_data: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    """
    arrange: Given a charm with mocked lightkube client, juju secret, relations and gateway ip.
    act: update the charm's config with the correct values.
    assert: the charm goes into active status with the message showing the correct gateway ip.
    """
    mock_lightkube_client.list = MagicMock(return_value=[gateway_class_resource])
    mock_lightkube_client.get = MagicMock(
        return_value=GenericNamespacedResource(status={"addresses": [{"value": "10.0.0.0"}]}),
    )
    monkeypatch.setattr("ops.jujuversion.JujuVersion.has_secrets", PropertyMock(return_value=True))
    password, private_key = private_key_and_password
    juju_secret_mock = MagicMock(spec=Secret)
    juju_secret_mock.get_content.return_value = {"key": private_key, "password": password}
    monkeypatch.setattr("ops.model.Model.get_secret", MagicMock(return_value=juju_secret_mock))
    monkeypatch.setattr(
        "charms.traefik_k8s.v2.ingress.IngressPerAppProvider.publish_url",
        MagicMock(),
    )
    monkeypatch.setattr(
        "resource_manager.secret.SecretResourceManager.define_resource",
        MagicMock(),
    )
    monkeypatch.setattr(
        "state.http_route.HTTPRouteResourceDefinition.from_charm",
        MagicMock(),
    )
    monkeypatch.setattr(
        "charms.traefik_k8s.v2.ingress.IngressPerAppProvider.publish_url",
        MagicMock(),
    )

    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    harness.add_relation("gateway", "hello-kubecon", app_data={})
    harness.begin()
    harness.update_config(
        {"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG, "gateway-class": GATEWAY_CLASS_CONFIG}
    )

    config = CharmConfig.from_charm(harness.charm, lightkube_client_mock)
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
    exc: type[Exception],
):
    """
    arrange: given a charm with mocked lightkube client and resource manager
    that raises CreateGatewayError and InvalidResourceError.
    act: when agent reconciliation triggers.
    assert: the gateway resource is created with the expected values.
    """
    harness.add_relation(
        "gateway",
        "ingress-requirer",
        app_data=gateway_relation_application_data,
        unit_data=gateway_relation_unit_data,
    )
    relation_id = harness.add_relation("certificates", "self-signed-certificates")
    harness.update_relation_data(relation_id, harness.model.app.name, certificates_relation_data)
    harness.set_leader()
    harness.begin()
    monkeypatch.setattr("charm.TLSRelationService", MagicMock(spec=TLSRelationService))
    monkeypatch.setattr(
        "resource_manager.gateway.GatewayResourceManager.define_resource",
        MagicMock(side_effect=exc("Error message.")),
    )
    monkeypatch.setattr(
        "resource_manager.secret.SecretResourceManager.define_resource",
        MagicMock(),
    )
    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    harness.begin()

    with pytest.raises(RuntimeError):
        harness.update_config(
            {
                "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
                "gateway-class": GATEWAY_CLASS_CONFIG,
            }
        )


def test_gateway_resource_definition_insufficient_permission(
    harness: Harness,
    certificates_relation_data: Dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
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
        "charm.get_client",
        lightkube_client_mock,
    )

    harness.begin()
    harness.update_config(
        {
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        }
    )

    assert harness.charm.unit.status.name == ops.BlockedStatus.name


def test_gateway_resource_definition_api_error_not_403(
    harness: Harness,
    certificates_relation_data: Dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
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
        "charm.get_client",
        lightkube_client_mock,
    )

    harness.begin()
    with pytest.raises(ApiError):
        harness.update_config(
            {
                "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
                "gateway-class": GATEWAY_CLASS_CONFIG,
            }
        )


def test_gateway_gen_resource(harness: Harness):
    harness.update_config(
        {
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        }
    )
    client_mock = MagicMock(spec=Client)
    client_mock.list = MagicMock(
        return_value=[GenericGlobalResource(metadata=ObjectMeta(name=GATEWAY_CLASS_CONFIG))]
    )
    harness.begin()
    charm = harness.charm
    gateway_resource_definition = GatewayResourceDefinition.from_charm(charm)
    gateway_resource_manager = GatewayResourceManager(
        labels=harness.charm._labels,
        client=client_mock,
    )
    secret_resource_definition = SecretResourceDefinition.from_charm(harness.charm)
    config = CharmConfig.from_charm(harness.charm, client_mock)
    gateway_resource = gateway_resource_manager._gen_resource(
        gateway_resource_definition, config, secret_resource_definition
    )
    assert gateway_resource.spec["gatewayClassName"] == GATEWAY_CLASS_CONFIG
    assert len(gateway_resource.spec["listeners"])


@pytest.mark.parametrize(
    "exc",
    [
        pytest.param(AttributeError, id="AttributeError."),
        pytest.param(TypeError, id="TypeError."),
        pytest.param(KeyError, id="KeyError."),
    ],
)
def test_gateway_resource_definition_get_gateway_address_error(
    harness: Harness,
    certificates_relation_data: Dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    exc: type[Exception],
):
    """
    arrange: given a charm with mocked lightkube client and resource manager.
    act: when agent reconciliation triggers.
    assert: the gateway resource is created with the expected values.
    """
    lightkube_client_mock = MagicMock(spec=Client)
    lightkube_client_mock.return_value.get = MagicMock(
        side_effect=exc,
    )
    monkeypatch.setattr("charm.KubeConfig", MagicMock())
    monkeypatch.setattr("charm.Client", lightkube_client_mock)
    monkeypatch.setattr("charm.TLSRelationService", MagicMock(spec=TLSRelationService))
    define_resource_mock = MagicMock()
    monkeypatch.setattr(
        "resource_manager.gateway.GatewayResourceManager.define_resource", define_resource_mock
    )
    charm_config_mock = MagicMock(spec=CharmConfig)
    monkeypatch.setattr(
        "state.config.CharmConfig.from_charm", MagicMock(return_value=charm_config_mock)
    )
    monkeypatch.setattr(
        "resource_manager.secret.SecretResourceManager.define_resource",
        MagicMock(),
    )
    monkeypatch.setattr(
        "state.http_route.HTTPRouteResourceDefinition.from_charm",
        MagicMock(),
    )
    monkeypatch.setattr(
        "charms.traefik_k8s.v2.ingress.IngressPerAppProvider.publish_url",
        MagicMock(),
    )

    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    harness.add_relation("gateway", "hello-kubecon", app_data={})
    harness.begin()
    harness.update_config(
        {"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG, "gateway-class": GATEWAY_CLASS_CONFIG}
    )

    assert harness.charm.unit.status.name == ops.WaitingStatus.name
