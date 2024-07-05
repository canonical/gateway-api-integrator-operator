# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for gateway-api-integrator charm unit tests."""

from unittest.mock import MagicMock

import pytest
from lightkube.core.client import Client
from lightkube.generic_resource import GenericGlobalResource
from lightkube.models.meta_v1 import ObjectMeta
from ops.testing import Harness

from charm import GatewayAPICharm
from tls_relation import TLSRelationService, generate_private_key

TEST_EXTERNAL_HOSTNAME_CONFIG = "gateway.internal"
GATEWAY_CLASS_CONFIG = "cilium"


@pytest.fixture(scope="function", name="harness")
def harness_fixture():
    """Enable ops test framework harness."""
    harness = Harness(GatewayAPICharm)
    yield harness
    harness.cleanup()


@pytest.fixture(scope="function", name="certificates_relation_data")
def certificates_relation_data_fixture(mock_certificate: str) -> dict[str, str]:
    """Mock tls_certificates relation data."""
    return {
        f"csr-{TEST_EXTERNAL_HOSTNAME_CONFIG}": "whatever",
        f"certificate-{TEST_EXTERNAL_HOSTNAME_CONFIG}": mock_certificate,
        f"ca-{TEST_EXTERNAL_HOSTNAME_CONFIG}": "whatever",
        f"chain-{TEST_EXTERNAL_HOSTNAME_CONFIG}": "whatever",
    }


@pytest.fixture(scope="function", name="patch_lightkube_client")
def patch_lightkube_client_fixture(
    monkeypatch: pytest.MonkeyPatch,
):
    """Patch lightkube cluster initialization."""
    monkeypatch.setattr("charm.KubeConfig", MagicMock())
    monkeypatch.setattr("charm.Client", MagicMock())


@pytest.fixture(scope="function", name="mock_lightkube_client")
def mock_lightkube_client_fixture(monkeypatch: pytest.MonkeyPatch) -> Client:
    lightkube_client_mock = MagicMock(spec=Client)
    monkeypatch.setattr("charm._get_client", MagicMock(return_value=lightkube_client_mock))
    return lightkube_client_mock


@pytest.fixture(scope="function", name="gateway_class_resource")
def gateway_class_resource_fixture():
    return GenericGlobalResource(metadata=ObjectMeta(name=GATEWAY_CLASS_CONFIG))


@pytest.fixture(scope="function", name="private_key_and_password")
def private_key_and_password_fixture(harness: Harness) -> tuple[str, str]:
    """Patch lightkube cluster initialization."""
    tls = TLSRelationService(harness.model)
    password = tls.generate_password().encode()
    private_key = generate_private_key(password=password)
    return (password.decode(), private_key.decode())


@pytest.fixture(scope="function", name="mock_certificate")
def mock_certificate_fixture() -> str:
    return (
        "-----BEGIN CERTIFICATE-----"
        "MIIDgDCCAmigAwIBAgIUa32Vp4pS2WjrTNG7SZJ66SdMs2YwDQYJKoZIhvcNAQEL"
        "BQAwOTELMAkGA1UEBhMCVVMxKjAoBgNVBAMMIXNlbGYtc2lnbmVkLWNlcnRpZmlj"
        "YXRlcy1vcGVyYXRvcjAeFw0yNDA3MDMxODE0MjBaFw0yNTA3MDMxODE0MjBaMEox"
        "GTAXBgNVBAMMEGdhdGV3YXkuaW50ZXJuYWwxLTArBgNVBC0MJDRmZmM4YjZlLTA0"
        "MGUtNDIxZC1hOGJhLTNhOTAzMzQxYjg1MzCCASIwDQYJKoZIhvcNAQEBBQADggEP"
        "ADCCAQoCggEBAJVOj9tOjA6zidDoSpqR4ObnTIouqdbXoibFB8/QlE7KiLkvUe4z"
        "F53ATHMeXOvJ7/q8sAyyOsHIjmPOf7TSh2lrrZCiwmsy5ma8oNQewps+VJR3tLgb"
        "OEh2ygpTaEPEK1Xz7zwwRU8EJrRuSo4L37iJJTcu2nubLWvBnzqWE1bYBbV8msH/"
        "xP88kojbDuufND6ad1qZf1YPmxzbXTlWtYrlGXrvRWf5fP2AWZYwOX4e8m32Xa/m"
        "z+1vb0xm2YrLqmjC+un0es+XaXSYyh1ZS5t42QW6J5nRwq0z4KOaRjOb9dq+T4nL"
        "ZdkPn61cRNyY7E+xZ+TqMXGtlNXzTkXcJ3ECAwEAAaNvMG0wIQYDVR0jBBowGIAW"
        "BBQ8ihb2ukCPiqijvCUaZ6HjYE9slDAdBgNVHQ4EFgQUwQYmWRBZk02AYVbx49QW"
        "kiVuu2owDAYDVR0TAQH/BAIwADAbBgNVHREEFDASghBnYXRld2F5LmludGVybmFs"
        "MA0GCSqGSIb3DQEBCwUAA4IBAQADD9FU7rU9ZMqzAAnQ+POpOau9l25/27Itx64W"
        "BHsIDx29yUCJTKBeV1yU8jlEp6r3H6ntQJO2jke3qQzDPF7eWOyCFhohMRHT9M6N"
        "r9xzrAaqd2OdQ8xlYqvXJ8JXmUfWE5jstUHK10KBsXjBZdfOTLGhg3kHw72cg/MJ"
        "bB0JcLv2Lf/sFgU68bEWampwgjlAuybGKSTh+tiJXm2G14eCnI5xEMwezJQS+J+7"
        "YXZZ153/uJZ5N8hIo9ld0LcYX5l7YrM1GH8CQ5GXN9kTgmRrpuSp/bZKd7GFmRq1"
        "4+3+0/6Ba2Zlt9fu4PixG+XukQnBIxtIMjWp7q7xWp8F4aOW"
        "-----END CERTIFICATE-----"
    )
