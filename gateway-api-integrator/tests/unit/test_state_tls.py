# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for TLSInformation dataclass."""

import pytest
from pydantic import ValidationError

from state.tls import TLSInformation


def test_valid_tls_information():
    """
    arrange: Provide valid values for all TLSInformation fields.
    act: Instantiate TLSInformation.
    assert: All fields are correctly set.
    """
    info = TLSInformation(
        secret_resource_name_prefix="my-app-secret",
        tls_certs={"gateway.internal": "cert-data"},
        tls_keys={"gateway.internal": "key-data"},
    )
    assert info.secret_resource_name_prefix == "my-app-secret"
    assert info.tls_certs == {"gateway.internal": "cert-data"}
    assert info.tls_keys == {"gateway.internal": "key-data"}


def test_hostname_property():
    """
    arrange: Provide valid TLSInformation with a single cert/key pair.
    act: Access the hostname property.
    assert: The hostname matches the key in tls_certs.
    """
    info = TLSInformation(
        secret_resource_name_prefix="my-app-secret",
        tls_certs={"gateway.internal": "cert-data"},
        tls_keys={"gateway.internal": "key-data"},
    )
    assert info.hostname == "gateway.internal"


def test_invalid_hostname_key_in_tls_certs():
    """
    arrange: Provide an invalid domain as a key in tls_certs.
    act: Instantiate TLSInformation.
    assert: ValidationError is raised by the valid_fqdn BeforeValidator.
    """
    with pytest.raises(ValidationError):
        TLSInformation(
            secret_resource_name_prefix="my-app-secret",
            tls_certs={"not a valid hostname!": "cert-data"},
            tls_keys={"gateway.internal": "key-data"},
        )


def test_invalid_hostname_key_in_tls_keys():
    """
    arrange: Provide an invalid domain as a key in tls_keys.
    act: Instantiate TLSInformation.
    assert: ValidationError is raised by the valid_fqdn BeforeValidator.
    """
    with pytest.raises(ValidationError):
        TLSInformation(
            secret_resource_name_prefix="my-app-secret",
            tls_certs={"gateway.internal": "cert-data"},
            tls_keys={"not a valid hostname!": "key-data"},
        )


def test_multiple_cert_key_pairs_rejected():
    """
    arrange: Provide two cert/key pairs.
    act: Instantiate TLSInformation.
    assert: ValidationError is raised because only 1 pair is supported.
    """
    with pytest.raises(ValidationError):
        TLSInformation(
            secret_resource_name_prefix="my-app-secret",
            tls_certs={"a.example.com": "cert-a", "b.example.com": "cert-b"},
            tls_keys={"a.example.com": "key-a", "b.example.com": "key-b"},
        )


def test_empty_certs_and_keys_rejected():
    """
    arrange: Provide empty tls_certs and tls_keys dicts.
    act: Instantiate TLSInformation.
    assert: ValidationError is raised because exactly 1 pair is required.
    """
    with pytest.raises(ValidationError):
        TLSInformation(
            secret_resource_name_prefix="my-app-secret",
            tls_certs={},
            tls_keys={},
        )


def test_mismatched_cert_and_key_hostnames_rejected():
    """
    arrange: Provide tls_certs and tls_keys with different hostname keys.
    act: Instantiate TLSInformation.
    assert: ValidationError is raised because hostnames must match.
    """
    with pytest.raises(ValidationError):
        TLSInformation(
            secret_resource_name_prefix="my-app-secret",
            tls_certs={"gateway.internal": "cert-data"},
            tls_keys={"other.internal": "key-data"},
        )
