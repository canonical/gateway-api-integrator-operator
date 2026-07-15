# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Disable protected access rules due to the need to test charm._labels
# pylint: disable=protected-access
"""Unit tests for secret resource."""

import json
from unittest.mock import MagicMock

import pytest
from ops import testing

from charm import GatewayAPICharm
from resource_manager.secret import (
    SecretResourceDefinition,
    TLSSecretResourceManager,
)
from state.tls import TLSInformation

from .conftest import GATEWAY_CLASS_CONFIG, TEST_EXTERNAL_HOSTNAME_CONFIG


@pytest.mark.usefixtures("client_with_mock_external")
def test_secret_gen_resource(
    gateway_relation: testing.Relation,
    certificates_relation: testing.Relation,
    mock_certificates_relation_data: str,
    mock_lightkube_client: MagicMock,
) -> None:
    """
    arrange: Given a charm with valid config and mocked client.
    act: Call _gen_resource from the required state components.
    assert: The k8s resource is correctly generated.
    """
    ctx = testing.Context(GatewayAPICharm)
    state_in = testing.State(
        leader=True,
        config={
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        },
        relations=[gateway_relation, certificates_relation],
    )

    with ctx(ctx.on.update_status(), state_in) as manager:
        charm = manager.charm
        charm.certificates.get_private_key = MagicMock(return_value="key-data")
        secret_resource_manager = TLSSecretResourceManager(
            labels=charm._labels,
            client=mock_lightkube_client,
        )
        tls_information = TLSInformation.from_charm(
            charm,
            {TEST_EXTERNAL_HOSTNAME_CONFIG},
            charm.certificates,
        )
        secret_resource = secret_resource_manager._gen_resource(
            SecretResourceDefinition.from_tls_information(
                tls_information,
                TEST_EXTERNAL_HOSTNAME_CONFIG,
            )
        )

        assert (
            secret_resource.metadata.name
            == f"{charm.app.name}-secret-{TEST_EXTERNAL_HOSTNAME_CONFIG}"
        )
        expected_data = json.loads(mock_certificates_relation_data)[0]
        assert secret_resource.stringData["tls.crt"] == "\n\n".join(
            [expected_data["certificate"], expected_data["ca"]]
        )
