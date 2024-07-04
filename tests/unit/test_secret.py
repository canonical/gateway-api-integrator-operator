# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for secret resource."""
from unittest.mock import MagicMock, PropertyMock

import pytest
from lightkube.core.client import Client
from lightkube.generic_resource import GenericGlobalResource
from lightkube.models.meta_v1 import ObjectMeta
from ops.model import Secret
from ops.testing import Harness

from resource_manager.secret import SecretResourceManager, _get_decrypted_key
from state.config import CharmConfig
from state.secret import SecretResourceDefinition
from state.tls import TLSInformation

from .conftest import GATEWAY_CLASS_CONFIG, TEST_EXTERNAL_HOSTNAME_CONFIG


def test_secret_get_decrypted_key(harness: Harness, private_key_and_password: tuple[str, str]):
    """
    arrange: given a GatewayApiIntegrator charm.
    act: generate a private key and decrypt it.
    assert: the decrypt operation pass without any error.
    """
    password, private_key = private_key_and_password
    harness.begin()

    decrypted_key = _get_decrypted_key(private_key, password)

    assert decrypted_key


def test_get_hostname_from_cert(harness: Harness, mock_certificate: str):
    harness.begin()
    assert (
        harness.charm._tls.get_hostname_from_cert(mock_certificate)
        == TEST_EXTERNAL_HOSTNAME_CONFIG
    )


def test_secret_gen_resource(
    harness: Harness,
    certificates_relation_data: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    private_key_and_password: tuple[str, str],
):
    password, private_key = private_key_and_password
    client_mock = MagicMock(spec=Client)
    client_mock.list = MagicMock(
        return_value=[GenericGlobalResource(metadata=ObjectMeta(name=GATEWAY_CLASS_CONFIG))]
    )
    monkeypatch.setattr("ops.jujuversion.JujuVersion.has_secrets", PropertyMock(return_value=True))
    juju_secret_mock = MagicMock(spec=Secret)
    juju_secret_mock.get_content.return_value = {"key": private_key, "password": password}

    monkeypatch.setattr("ops.model.Model.get_secret", MagicMock(return_value=juju_secret_mock))

    harness.update_config(
        {
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        }
    )
    relation_id = harness.add_relation("certificates", "self-signed-certificates")
    harness.update_relation_data(relation_id, harness.model.app.name, certificates_relation_data)

    harness.begin()
    charm = harness.charm
    secret_resource_definition = SecretResourceDefinition.from_charm(charm)
    secret_resource_manager = SecretResourceManager(
        labels=harness.charm._labels,
        client=client_mock,
    )
    secret_resource_definition = SecretResourceDefinition.from_charm(harness.charm)
    tls_information = TLSInformation.from_charm(charm)
    config = CharmConfig.from_charm(harness.charm, client_mock)
    secret_resource = secret_resource_manager._gen_resource(
        secret_resource_definition, config, tls_information
    )
    assert (
        secret_resource.metadata.name
        == f"{harness.model.app.name}-secret-{TEST_EXTERNAL_HOSTNAME_CONFIG}"
    )
    assert (
        secret_resource.stringData["tls.crt"]
        == certificates_relation_data[f"chain-{TEST_EXTERNAL_HOSTNAME_CONFIG}"]
    )
