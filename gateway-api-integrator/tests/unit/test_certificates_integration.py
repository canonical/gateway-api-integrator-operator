# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for certificates integration."""

from unittest.mock import MagicMock

import ops
import pytest
from ops.model import Secret, SecretNotFoundError
from ops.testing import Harness
from state.tls import TLSInformation, TlsIntegrationMissingError

from .conftest import GATEWAY_CLASS_CONFIG, TEST_EXTERNAL_HOSTNAME_CONFIG


@pytest.mark.skip(reason="TLSRelationService no longer exists in v4 - password generation is handled automatically")
@pytest.mark.usefixtures("patch_lightkube_client")
def test_generate_password(harness: Harness):
    """
    arrange: Given a gateway api integrator charm.
    act: run generate password.
    assert: TLSRelationService no longer exists in v4.
    """
    # In v4, password generation is handled internally by the library
    pass


@pytest.mark.usefixtures("client_with_mock_external")
def test_cert_relation_secret_not_found_error(
    harness: Harness,
    certificates_relation_data: dict[str, str],
    gateway_relation: dict[str, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
    config: dict[str, str],
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
    harness.add_relation(
        "gateway",
        "requirer-charm",
        app_data=gateway_relation["app_data"],
        unit_data=gateway_relation["unit_data"],
    )
    harness.set_leader()
    harness.update_config(config)
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


@pytest.mark.skip(reason="v4 handles certificate renewal automatically")
@pytest.mark.usefixtures("client_with_mock_external")
def test_cert_relation_certificate_expiring(
    harness: Harness, certificates_relation_data: dict[str, str], monkeypatch: pytest.MonkeyPatch
):
    """
    arrange: Given a charm with valid certificates integration data.
    act: Fire certificate_expiring event.
    assert: certificate_expiring event is not handled in v4 (automatic renewal).
    """
    # In v4, certificate renewal is handled automatically via refresh_events
    # This test is kept for documentation but skipped
    pass


@pytest.mark.skip(reason="v4 does not have certificate_invalidated event handler")
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
    assert: certificate_invalidated event is not handled in v4.
    """
    # In v4, certificate_invalidated event handler is not implemented
    # as it's commented out in charm.py
    pass


@pytest.mark.skip(reason="v4 does not have all_certificates_invalidated event handler")
@pytest.mark.usefixtures("client_with_mock_external")
def test_cert_relation_all_certificates_invalidated(
    harness: Harness,
    gateway_relation: dict[str, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
    certificates_relation_data: dict[str, str],
    config: dict[str, str],
):  # pylint: disable=too-many-arguments, too-many-positional-arguments
    """
    arrange: Given a charm with valid certificates integration data.
    act: Fire all_certificates_invalidated event.
    assert: all_certificates_invalidated event is not handled in v4.
    """
    # In v4, all_certificates_invalidated event handler is not implemented
    # as it's commented out in charm.py
    pass


@pytest.mark.skip(reason="v4 does not have all_certificates_invalidated event handler")
@pytest.mark.usefixtures("client_with_mock_external")
def test_cert_relation_all_certificates_invalidated_secret_not_found(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
    certificates_relation_data: dict[str, str],
    config: dict[str, str],
):
    """
    arrange: Given a charm with valid certificates integration data and no juju secret.
    act: Fire all_certificates_invalidated event.
    assert: all_certificates_invalidated event is not handled in v4.
    """
    # In v4, all_certificates_invalidated event handler is not implemented
    # as it's commented out in charm.py
    pass


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
    reconcile_mock = MagicMock()
    monkeypatch.setattr("charm.GatewayAPICharm._reconcile", reconcile_mock)

    relation_id = harness.add_relation("certificates", "self-signed-certificates")
    harness.update_relation_data(relation_id, harness.model.app.name, certificates_relation_data)
    harness.set_leader()
    harness.begin()

    harness.charm.certificates.on.certificate_available.emit(
        certificates_relation_data[f"certificate-{TEST_EXTERNAL_HOSTNAME_CONFIG}"],
        "csr",
        certificates_relation_data[f"ca-{TEST_EXTERNAL_HOSTNAME_CONFIG}"],
        certificates_relation_data[f"chain-{TEST_EXTERNAL_HOSTNAME_CONFIG}"],
    )
    reconcile_mock.assert_called_once()


@pytest.mark.skip(reason="TLSRelationService no longer exists in v4")
@pytest.mark.usefixtures("mock_certificate")
def test_revoke_all_certificates(harness: Harness, monkeypatch: pytest.MonkeyPatch):
    """
    arrange: Given a TLS relation service with mocked provider certificate.
    act: revoke all certificates.
    assert: TLSRelationService no longer exists in v4.
    """
    # In v4, certificate revocation is handled via TLSCertificatesRequiresV4.revoke_all_certificates()
    # without needing a separate TLSRelationService class
    pass


@pytest.mark.skip(reason="TLSRelationService no longer exists in v4 - certificates are requested automatically")
@pytest.mark.usefixtures("juju_secret_mock")
def test_request_certificates(harness: Harness, monkeypatch: pytest.MonkeyPatch):
    """
    arrange: Given a charm with mocked juju secret.
    act: Call request certificate.
    assert: TLSRelationService no longer exists in v4.
    """
    # In v4, certificates are requested automatically via the certificate_requests parameter
    # passed during TLSCertificatesRequiresV4 initialization
    pass
