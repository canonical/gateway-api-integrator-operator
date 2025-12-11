# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for certificates integration."""

from unittest.mock import MagicMock

import ops
import pytest
import tls_relation
from ops.model import Secret, SecretNotFoundError
from ops.testing import Harness
from state.tls import TLSInformation, TlsIntegrationMissingError

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG


@pytest.mark.usefixtures("client_with_mock_external")
def test_generate_password(harness: Harness):
    """
    arrange: Given a gateway api integrator charm.
    act: run generate password.
    assert: the password generated has the correct format.
    """
    harness.begin()

    tls_rel = tls_relation.TLSRelationService(harness.model, harness.charm.certificates)

    password = tls_rel.generate_password()
    assert isinstance(password, str)
    assert len(password) == 12


@pytest.mark.usefixtures("client_with_mock_external")
def test_cert_relation_secret_not_found_error(
    harness: Harness,
    certificates_relation_data: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    """
    arrange: Given a charm with mocked tls module methods and valid config.
    act: when relation with a TLS provider is established.
    assert: the charm correctly generates a password and a CSR.
    """
    monkeypatch.setattr(
        "ops.model.Model.get_secret",
        MagicMock(side_effect=SecretNotFoundError),
    )
    harness.set_leader()
    harness.begin()

    with pytest.raises(SecretNotFoundError):
        harness.add_relation(
            "certificates", "self-signed-certificates", app_data=certificates_relation_data
        )


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


@pytest.mark.usefixtures("client_with_mock_external")
def test_cert_relation_certificate_expiring(
    harness: Harness, certificates_relation_data: dict[str, str], monkeypatch: pytest.MonkeyPatch
):
    """
    arrange: Given a charm with valid certificates integration data.
    act: Fire certificate_expiring event.
    assert: request_certificate_renewal lib method is called once.
    """
    request_certificate_renewal_mock = MagicMock()
    monkeypatch.setattr(
        (
            "charms.tls_certificates_interface.v3.tls_certificates"
            ".TLSCertificatesRequiresV3.request_certificate_renewal"
        ),
        request_certificate_renewal_mock,
    )
    harness.set_leader()
    relation_id = harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    harness.update_relation_data(
        relation_id, harness.model.app.name, {f"csr-{TEST_EXTERNAL_HOSTNAME_CONFIG}": "csr"}
    )
    harness.begin()

    harness.charm.certificates.on.certificate_expiring.emit(
        certificates_relation_data[f"certificate-{TEST_EXTERNAL_HOSTNAME_CONFIG}"], "now"
    )

    request_certificate_renewal_mock.assert_called_once()


@pytest.mark.usefixtures("client_with_mock_external")
@pytest.mark.parametrize(
    "reason",
    [
        pytest.param("expired", id="expired."),
        pytest.param("revoked", id="revoked."),
    ],
)
def test_cert_relation_certificate_invalidated(
    harness: Harness,
    certificates_relation_data: dict[str, str],
    reason: str,
):
    """
    arrange: Given a charm with valid certificates integration data.
    act: Fire certificate_invalidated event.
    assert: The charm is in Maintenance status to wait for new cert.
    """
    harness.set_leader()
    relation_id = harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    harness.update_relation_data(
        relation_id, harness.model.app.name, {f"csr-{TEST_EXTERNAL_HOSTNAME_CONFIG}": "csr"}
    )

    harness.begin()
    harness.charm.certificates.on.certificate_invalidated.emit(
        reason,
        certificates_relation_data[f"certificate-{TEST_EXTERNAL_HOSTNAME_CONFIG}"],
        "csr",
        certificates_relation_data[f"ca-{TEST_EXTERNAL_HOSTNAME_CONFIG}"],
        certificates_relation_data[f"chain-{TEST_EXTERNAL_HOSTNAME_CONFIG}"],
    )

    assert harness.charm.unit.status.name == ops.MaintenanceStatus.name


@pytest.mark.usefixtures("client_with_mock_external")
def test_cert_relation_all_certificates_invalidated(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
    certificates_relation_data: dict[str, str],
):
    """
    arrange: Given a charm with valid certificates integration data.
    act: Fire all_certificates_invalidated event.
    assert: The remove_all_revisions method is called once.
    """
    juju_secret_mock = MagicMock(spec=Secret)
    monkeypatch.setattr("ops.model.Model.get_secret", MagicMock(return_value=juju_secret_mock))
    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    harness.begin()

    harness.charm.certificates.on.all_certificates_invalidated.emit()

    juju_secret_mock.remove_all_revisions.assert_called_once()


@pytest.mark.usefixtures("client_with_mock_external")
def test_cert_relation_all_certificates_invalidated_secret_not_found(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
    certificates_relation_data: dict[str, str],
):
    """
    arrange: Given a charm with valid certificates integration data and no juju.
    act: Fire all_certificates_invalidated event.
    assert: The remove_all_revisions method is not called.
    """
    juju_secret_mock = MagicMock(spec=Secret)
    monkeypatch.setattr(
        "ops.model.Model.get_secret",
        MagicMock(return_value=juju_secret_mock, side_effect=SecretNotFoundError),
    )
    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    harness.begin()

    harness.charm.certificates.on.all_certificates_invalidated.emit()

    juju_secret_mock.remove_all_revisions.assert_not_called()


@pytest.mark.usefixtures("mock_certificate")
@pytest.mark.usefixtures("client_with_mock_external")
def test_revoke_all_certificates(harness: Harness, monkeypatch: pytest.MonkeyPatch):
    """
    arrange: Given a TLS relation service with mocked provider certificate.
    act: .
    assert: The _reconcile method is called once.
    """
    harness.add_relation("certificates", "self-signed-certificates")
    secret_mock = MagicMock()
    secret_mock.remove_all_revisions = MagicMock(side_effect=SecretNotFoundError)
    harness.begin()
    monkeypatch.setattr("ops.model.Model.get_secret", MagicMock(return_value=secret_mock))
    request_certificate_revocation_mock = MagicMock()
    monkeypatch.setattr(
        (
            "charms.tls_certificates_interface.v3.tls_certificates"
            ".TLSCertificatesRequiresV3.request_certificate_revocation"
        ),
        request_certificate_revocation_mock,
    )
    tls = tls_relation.TLSRelationService(harness.model, harness.charm.certificates)
    tls.revoke_all_certificates()
    request_certificate_revocation_mock.assert_called_once()


@pytest.mark.usefixtures("juju_secret_mock")
@pytest.mark.usefixtures("client_with_mock_external")
def test_request_certificates(harness: Harness, monkeypatch: pytest.MonkeyPatch):
    """
    arrange: Given a char with mocked juju secret.
    act: Call request certificate.
    assert: The library method is correctly called.
    """
    request_certificate_creation_mock = MagicMock()
    monkeypatch.setattr(
        (
            "charms.tls_certificates_interface.v3.tls_certificates"
            ".TLSCertificatesRequiresV3.request_certificate_creation"
        ),
        request_certificate_creation_mock,
    )
    harness.begin()
    tls = tls_relation.TLSRelationService(harness.model, harness.charm.certificates)
    tls.request_certificate(TEST_EXTERNAL_HOSTNAME_CONFIG)
    request_certificate_creation_mock.assert_called_once()
