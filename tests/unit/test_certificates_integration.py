# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for certificates integration."""

import typing
from unittest.mock import MagicMock, PropertyMock

import ops
import pytest
from lightkube.core.client import Client
from lightkube.generic_resource import GenericGlobalResource
from lightkube.models.meta_v1 import ObjectMeta
from ops.model import Secret, SecretNotFoundError
from ops.testing import Harness

import tls_relation
from state.tls import TLSInformation, TlsIntegrationMissingError
from tls_relation import SecretNotSupportedException
from .conftest import GATEWAY_CLASS_CONFIG, TEST_EXTERNAL_HOSTNAME_CONFIG


@pytest.mark.usefixtures("patch_lightkube_client")
def test_generate_password(harness: Harness):
    """
    arrange: Given a gateway api integrator charm.
    act: run generate password.
    assert: the password generated has the correct format.
    """
    harness.begin()

    tls_rel = tls_relation.TLSRelationService(harness.charm.model)

    password = tls_rel.generate_password()
    assert isinstance(password, str)
    assert len(password) == 12


@pytest.mark.parametrize(
    "has_secrets",
    [
        pytest.param(True, id="has secrets."),
        pytest.param(False, id="does not have secrets."),
    ],
)
@pytest.mark.parametrize(
    "get_secret_exc",
    [
        pytest.param(None, id="no error."),
        pytest.param(SecretNotFoundError, id="secret_not_found_error."),
    ],
)
def test_cert_relation(
    harness: Harness,
    certificates_relation_data: dict[str, str],
    private_key_and_password: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
    get_secret_exc: typing.Optional[type[SecretNotFoundError]],
    has_secrets: bool,
):
    """
    arrange: Given a charm with mocked tls module methods and valid config.
    act: when relation with a TLS provider is established.
    assert: the charm correctly generates a password and a CSR.
    """
    password, private_key = private_key_and_password

    lightkube_client_mock = MagicMock(spec=Client)
    lightkube_client_mock.list = MagicMock(
        return_value=[GenericGlobalResource(metadata=ObjectMeta(name=GATEWAY_CLASS_CONFIG))]
    )
    monkeypatch.setattr("charm.get_client", MagicMock(return_value=lightkube_client_mock))

    monkeypatch.setattr(
        "ops.jujuversion.JujuVersion.has_secrets",
        PropertyMock(return_value=has_secrets),
    )

    juju_secret_mock = MagicMock(spec=Secret)
    juju_secret_mock.get_content.return_value = {"key": private_key, "password": password}
    monkeypatch.setattr(
        "ops.model.Model.get_secret",
        MagicMock(return_value=juju_secret_mock, side_effect=get_secret_exc),
    )

    harness.set_leader()
    harness.update_config(
        {"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG, "gateway-class": GATEWAY_CLASS_CONFIG}
    )
    harness.begin()

    if has_secrets and not get_secret_exc:
        harness.add_relation(
            "certificates", "self-signed-certificates", app_data=certificates_relation_data
        )
    elif not has_secrets:
        with pytest.raises(SecretNotSupportedException):
            harness.add_relation(
                "certificates", "self-signed-certificates", app_data=certificates_relation_data
            )
    else:
        with pytest.raises(get_secret_exc):
            harness.add_relation(
                "certificates", "self-signed-certificates", app_data=certificates_relation_data
            )


def test_tls_information_integration_missing(harness: Harness):
    harness.begin()
    with pytest.raises(TlsIntegrationMissingError):
        TLSInformation.from_charm(harness.charm)


def test_tls_information_no_secret(
    harness: Harness,
    certificates_relation_data: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    relation_id = harness.add_relation("certificates", "self-signed-certificates")
    harness.update_relation_data(relation_id, harness.model.app.name, certificates_relation_data)
    harness.begin()
    monkeypatch.setattr(
        "ops.jujuversion.JujuVersion.has_secrets", PropertyMock(return_value=False)
    )
    with pytest.raises(SecretNotSupportedException):
        TLSInformation.from_charm(harness.charm)


def test_cert_relation_certificate_expiring(
    harness: Harness,
    certificates_relation_data: dict[str, str],
    private_key_and_password: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    password, private_key = private_key_and_password
    monkeypatch.setattr("ops.jujuversion.JujuVersion.has_secrets", PropertyMock(return_value=True))
    juju_secret_mock = MagicMock(spec=Secret)
    juju_secret_mock.get_content.return_value = {"key": private_key, "password": password}
    monkeypatch.setattr("ops.model.Model.get_secret", MagicMock(return_value=juju_secret_mock))
    monkeypatch.setattr(
        tls_relation.TLSRelationService,
        "get_hostname_from_cert",
        MagicMock(return_value=TEST_EXTERNAL_HOSTNAME_CONFIG),
    )
    harness.set_leader()
    harness.update_config(
        {"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG, "gateway-class": GATEWAY_CLASS_CONFIG}
    )
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
    private_key_and_password: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
    reason: str,
):
    password, private_key = private_key_and_password
    monkeypatch.setattr("ops.jujuversion.JujuVersion.has_secrets", PropertyMock(return_value=True))
    juju_secret_mock = MagicMock(spec=Secret)
    juju_secret_mock.get_content.return_value = {"key": private_key, "password": password}
    monkeypatch.setattr("ops.model.Model.get_secret", MagicMock(return_value=juju_secret_mock))
    monkeypatch.setattr(
        tls_relation.TLSRelationService,
        "get_hostname_from_cert",
        MagicMock(return_value=TEST_EXTERNAL_HOSTNAME_CONFIG),
    )
    harness.set_leader()
    harness.update_config(
        {"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG, "gateway-class": GATEWAY_CLASS_CONFIG}
    )
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


@pytest.mark.parametrize(
    "exc",
    [
        pytest.param(None, id="no error."),
        pytest.param(
            SecretNotFoundError,
            id="secret not found.",
        ),
    ],
)
def test_cert_relation_all_certificates_invalidated(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
    certificates_relation_data: dict[str, str],
    exc: typing.Optional[type[Exception]],
):
    lightkube_client_mock = MagicMock(spec=Client)
    lightkube_client_mock.list = MagicMock(
        return_value=[GenericGlobalResource(metadata=ObjectMeta(name=GATEWAY_CLASS_CONFIG))]
    )
    monkeypatch.setattr("charm.get_client", MagicMock(return_value=lightkube_client_mock))

    monkeypatch.setattr("ops.jujuversion.JujuVersion.has_secrets", PropertyMock(return_value=True))
    juju_secret_mock = MagicMock(spec=Secret)
    juju_get_secret_mock = MagicMock(return_value=juju_secret_mock)
    if exc:
        juju_get_secret_mock.side_effect = exc
    monkeypatch.setattr("ops.model.Model.get_secret", juju_get_secret_mock)
    harness.update_config(
        {"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG, "gateway-class": GATEWAY_CLASS_CONFIG}
    )
    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    harness.begin()
    harness.charm.certificates.on.all_certificates_invalidated.emit()
    if exc:
        juju_secret_mock.remove_all_revisions.assert_not_called()
    else:
        juju_secret_mock.remove_all_revisions.assert_called_once()


def test_certificate_available(
    harness: Harness,
    certificates_relation_data: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    private_key_and_password: tuple[str, str],
):
    reconcile_mock = MagicMock()
    monkeypatch.setattr("charm.GatewayAPICharm._reconcile", reconcile_mock)

    password, private_key = private_key_and_password
    monkeypatch.setattr("ops.jujuversion.JujuVersion.has_secrets", PropertyMock(return_value=True))
    juju_secret_mock = MagicMock(spec=Secret)
    juju_secret_mock.get_content.return_value = {"key": private_key, "password": password}
    monkeypatch.setattr("ops.model.Model.get_secret", MagicMock(return_value=juju_secret_mock))

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
