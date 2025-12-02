# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for certificates integration."""

from unittest.mock import MagicMock

import pytest
from ops.testing import Harness

from state.tls import TLSInformation, TlsIntegrationMissingError

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG


@pytest.mark.usefixtures("client_with_mock_external")
def test_cert_relation_secret_not_found_error(
    harness: Harness,
    certificates_relation_data: dict[str, str],
    config: dict[str, str],
):
    """
    arrange: Given a charm with mocked tls module methods and valid config.
    act: when relation with a TLS provider is established and secret is missing.
    assert: v4 library handles missing secret gracefully by auto-generating keys.
    """
    # V4 library auto-generates private keys when secret is not found
    # So we don't expect SecretNotFoundError anymore
    harness.set_leader()
    harness.update_config(config)
    harness.begin()

    # Should not raise an exception - v4 handles this gracefully
    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    # Verify the relation was added successfully
    assert harness.charm.certificates.private_key is not None


@pytest.mark.usefixtures("client_with_mock_external")
def test_tls_information_integration_missing(harness: Harness):
    """
    arrange: Given a charm with tls integration missing.
    act: Initialize TLSInformation state component.
    assert: TLSIntegrationMissingError is raised.
    """
    harness.begin()
    with pytest.raises(TlsIntegrationMissingError):
        TLSInformation.from_charm(harness.charm, harness.charm.certificates)


# Certificate expiring is handled automatically by v4 library


# Certificate invalidation is handled automatically by v4 library


# All certificates invalidation is handled automatically by v4 library


@pytest.mark.usefixtures("client_with_mock_external")
def test_certificate_available(
    harness: Harness,
    certificates_relation_data: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    """
    arrange: Given a charm with valid certificates integration data and mocked _reconcile method.
    act: Fire certificate_available event.
    assert: The _reconcile method is called once.
    """
    from charms.tls_certificates_interface.v4.tls_certificates import Certificate

    reconcile_mock = MagicMock()
    monkeypatch.setattr("charm.GatewayAPICharm._reconcile", reconcile_mock)

    relation_id = harness.add_relation("certificates", "self-signed-certificates")
    harness.update_relation_data(relation_id, harness.model.app.name, certificates_relation_data)
    harness.set_leader()
    harness.begin()

    from charms.tls_certificates_interface.v4.tls_certificates import (
        CertificateRequestAttributes,
        PrivateKey,
    )

    private_key = PrivateKey.generate()
    cert_attrs = CertificateRequestAttributes(sans_dns=[TEST_EXTERNAL_HOSTNAME_CONFIG])
    csr = cert_attrs.generate_csr(private_key)

    cert_key = f"certificate-{TEST_EXTERNAL_HOSTNAME_CONFIG}"
    ca_key = f"ca-{TEST_EXTERNAL_HOSTNAME_CONFIG}"
    chain_key = f"chain-{TEST_EXTERNAL_HOSTNAME_CONFIG}"
    cert = Certificate.from_string(certificates_relation_data[cert_key])
    ca = Certificate.from_string(certificates_relation_data[ca_key])
    chain = [Certificate.from_string(certificates_relation_data[chain_key])]

    harness.charm.certificates.on.certificate_available.emit(
        certificate=cert,
        certificate_signing_request=csr,
        ca=ca,
        chain=chain,
    )
    reconcile_mock.assert_called_once()


@pytest.mark.usefixtures("mock_certificate")
def test_revoke_all_certificates(harness: Harness, monkeypatch: pytest.MonkeyPatch):
    """
    arrange: Given a TLS relation service with mocked provider certificate.
    act: Call revoke_all_certificates.
    assert: The regenerate_private_key method is called once.
    """
    harness.add_relation("certificates", "self-signed-certificates")
    harness.begin()
    regenerate_private_key_mock = MagicMock()
    monkeypatch.setattr(
        (
            "charms.tls_certificates_interface.v4.tls_certificates"
            ".TLSCertificatesRequiresV4.regenerate_private_key"
        ),
        regenerate_private_key_mock,
    )
    regenerate_private_key_mock.assert_called_once()
