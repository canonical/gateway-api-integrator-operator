# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for gateway resource."""

from unittest.mock import MagicMock, PropertyMock

import ops
import pytest
from lightkube.core.client import Client
from lightkube.generic_resource import GenericGlobalResource, GenericNamespacedResource
from ops.model import Secret
from ops.testing import Harness

from .conftest import GATEWAY_CLASS_CONFIG, TEST_EXTERNAL_HOSTNAME_CONFIG


def test_create_gateway(
    harness: Harness,
    mock_lightkube_client: Client,
    gateway_class_resource: GenericGlobalResource,
    certificates_relation_data: dict[str, str],
    private_key_and_password: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    mock_lightkube_client.list = MagicMock(return_value=[gateway_class_resource])
    mock_lightkube_client.get = MagicMock(
        return_value=GenericNamespacedResource(status={"addresses": [{"value": "10.0.0.0"}]}),
    )
    monkeypatch.setattr("ops.jujuversion.JujuVersion.has_secrets", PropertyMock(return_value=True))
    password, private_key = private_key_and_password
    juju_secret_mock = MagicMock(spec=Secret)
    juju_secret_mock.get_content.return_value = {"key": private_key, "password": password}
    monkeypatch.setattr("ops.model.Model.get_secret", MagicMock(return_value=juju_secret_mock))
    relation_id = harness.add_relation("certificates", "self-signed-certificates")
    harness.update_relation_data(relation_id, harness.model.app.name, certificates_relation_data)
    harness.set_leader()
    harness.begin()

    harness.update_config(
        {
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        }
    )

    assert harness.charm.unit.status.name == ops.ActiveStatus.name
    assert "Gateway addresses: 10.0.0.0" == harness.charm.unit.status.message
