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
)
from state.tls import TLSInformation

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG


def test_secret_gen_resource(
    harness: Harness,
    certificates_relation_data: dict[str, str],
    client_with_mock_external: MagicMock,
    config: dict[str, str],
    gateway_relation: dict[str, dict[str, str]],
):
    """
    arrange: Given a charm with valid config and mocked client.
    act: Call _gen_resource from the required state components.
    assert: The k8s resource is correctly generated.
    """
    harness.update_config(config)
    harness.add_relation(
        "gateway",
        "requirer-charm",
        app_data=gateway_relation["app_data"],
        unit_data=gateway_relation["unit_data"],
    )
    relation_id = harness.add_relation("certificates", "self-signed-certificates")
    harness.update_relation_data(relation_id, harness.model.app.name, certificates_relation_data)

    harness.set_leader()
    harness.begin()
    harness.charm.certificates.get_private_key = MagicMock(return_value="key-data")
    secret_resource_manager = TLSSecretResourceManager(
        labels=harness.charm._labels,
        client=client_with_mock_external,
    )
    tls_information = TLSInformation.from_charm(
        harness.charm,
        {TEST_EXTERNAL_HOSTNAME_CONFIG},
        harness.charm.certificates,
    )
    secret_resource = secret_resource_manager._gen_resource(
        SecretResourceDefinition.from_tls_information(
            tls_information,
            TEST_EXTERNAL_HOSTNAME_CONFIG,
        )
    )

    assert (
        secret_resource.metadata.name
        == f"{harness.model.app.name}-secret-{TEST_EXTERNAL_HOSTNAME_CONFIG}"
    )
    assert (
        secret_resource.stringData["tls.crt"]
        == certificates_relation_data[f"certificate-{TEST_EXTERNAL_HOSTNAME_CONFIG}"]
    )
