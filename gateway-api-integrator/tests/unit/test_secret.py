# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Disable protected access rules due to the need to test charm._labels
# pylint: disable=protected-access
"""Unit tests for secret resource."""

from unittest.mock import MagicMock

from ops.testing import Harness
from resource_manager.secret import (
    SecretResourceDefinition,
    TLSSecretResourceManager,
    _get_decrypted_key,
)
from state.tls import TLSInformation
from tls_relation import get_hostname_from_cert

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG


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
    """
    arrange: Given a GatewayApiIntegrator charm.
    act: Get the hostname from an already generated cert.
    assert: The hostname is correct.
    """
    harness.begin()
    assert get_hostname_from_cert(mock_certificate) == TEST_EXTERNAL_HOSTNAME_CONFIG


def test_secret_gen_resource(
    harness: Harness,
    certificates_relation_data: dict[str, str],
    client_with_mock_external: MagicMock,
    config: dict[str, str],
):
    """
    arrange: Given a charm with valid config and mocked client.
    act: Call _gen_resource from the required state components.
    assert: The k8s resource is correctly generated.
    """
    harness.update_config(config)
    relation_id = harness.add_relation("certificates", "self-signed-certificates")
    harness.update_relation_data(relation_id, harness.model.app.name, certificates_relation_data)

    harness.begin()
    secret_resource_manager = TLSSecretResourceManager(
        labels=harness.charm._labels,
        client=client_with_mock_external,
    )
    tls_information = TLSInformation.from_charm(harness.charm, harness.charm.certificates)
    secret_resource = secret_resource_manager._gen_resource(
        SecretResourceDefinition.from_tls_information(tls_information, config["external-hostname"])
    )

    assert (
        secret_resource.metadata.name
        == f"{harness.model.app.name}-secret-{TEST_EXTERNAL_HOSTNAME_CONFIG}"
    )
    assert (
        secret_resource.stringData["tls.crt"]
        == certificates_relation_data[f"certificate-{TEST_EXTERNAL_HOSTNAME_CONFIG}"]
    )
