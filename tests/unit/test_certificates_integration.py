# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for certificates integration."""

from typing import Dict
from unittest.mock import MagicMock, PropertyMock

import ops
import pytest
from ops.testing import Harness

import tls_relation

from .conftest import GATEWAY_CLASS_CONFIG, TEST_EXTERNAL_HOSTNAME_CONFIG


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


def test_cert_relation(
    harness: Harness,
    certificates_relation_data: Dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    """
    arrange: Given a charm with mocked tls module methods and valid config.
    act: when relation with a TLS provider is established.
    assert: the charm correctly generates a password and a CSR.
    """
    generate_password_mock = MagicMock(return_value="123456789101")
    monkeypatch.setattr(
        tls_relation.TLSRelationService, "generate_password", generate_password_mock
    )
    monkeypatch.setattr(
        tls_relation.TLSRelationService, "update_relation_data_fields", MagicMock()
    )
    generate_csr_mock = MagicMock(return_value=b"csr")
    monkeypatch.setattr(tls_relation, "generate_csr", generate_csr_mock)
    has_secrets_mock = PropertyMock(return_value=True)
    monkeypatch.setattr(ops.JujuVersion, "has_secrets", has_secrets_mock)
    get_secret_mock = MagicMock()
    monkeypatch.setattr(ops.model.Model, "get_secret", get_secret_mock)

    harness.update_config(
        {"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG, "gateway-class": GATEWAY_CLASS_CONFIG}
    )
    harness.begin()
    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    generate_password_mock.assert_called_once()
    generate_csr_mock.assert_called_once()
    assert get_secret_mock.call_count == 2
