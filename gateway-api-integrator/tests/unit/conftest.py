# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for gateway-api-integrator charm unit tests."""

from unittest.mock import MagicMock, PropertyMock

import pytest
from charm import GatewayAPICharm
from charms.tls_certificates_interface.v4.tls_certificates import generate_private_key
from lightkube.core.client import Client
from lightkube.generic_resource import GenericGlobalResource, GenericNamespacedResource
from lightkube.models.meta_v1 import ObjectMeta
from ops.model import Secret
from ops.testing import Harness

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
        f"chain-{TEST_EXTERNAL_HOSTNAME_CONFIG}": mock_certificate,
    }


@pytest.fixture(scope="function", name="gateway_relation")
def gateway_relation_fixture() -> dict[str, dict[str, str]]:
    """Mock gateway relation data."""
    return {
        "app_data": {
            "name": '"gateway-api-integrator"',
            "model": '"testing"',
            "port": "8080",
            "strip_prefix": "false",
            "redirect_https": "false",
        },
        "unit_data": {"host": '"testing.ingress"', "ip": '"10.0.0.1"'},
    }


@pytest.fixture(scope="function", name="patch_lightkube_client")
def patch_lightkube_client_fixture(
    monkeypatch: pytest.MonkeyPatch,
):
    """Patch lightkube cluster initialization."""
    monkeypatch.setattr("client.KubeConfig", MagicMock())
    monkeypatch.setattr("client.Client", MagicMock())


@pytest.fixture(scope="function", name="mock_lightkube_client")
def mock_lightkube_client_fixture(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock lightkube client."""
    lightkube_client_mock = MagicMock(spec=Client)
    monkeypatch.setattr("charm.get_client", MagicMock(return_value=lightkube_client_mock))
    return lightkube_client_mock


@pytest.fixture(scope="function", name="gateway_class_resource")
def gateway_class_resource_fixture():
    """Mock gateway class global resource."""
    return GenericGlobalResource(metadata=ObjectMeta(name=GATEWAY_CLASS_CONFIG))


@pytest.fixture(scope="function", name="private_key")
def private_key_fixture() -> str:
    """Mock private key juju secret."""
    # In v4, password is not used for private key generation
    # Generate a simple private key for testing
    return str(generate_private_key())


@pytest.fixture(scope="function", name="juju_secret_mock")
def juju_secret_mock_fixture(
    monkeypatch: pytest.MonkeyPatch,
    private_key: str,
) -> tuple[str, str]:
    """Mock certificates integration."""
    juju_secret_mock = MagicMock(spec=Secret)
    juju_secret_mock.get_content.return_value = {"private-key": private_key}
    monkeypatch.setattr("ops.model.Model.get_secret", MagicMock(return_value=juju_secret_mock))
    return juju_secret_mock


@pytest.fixture(scope="function", name="mock_certificate")
def mock_certificate_fixture(monkeypatch: pytest.MonkeyPatch) -> str:
    """Mock tls certificate from a tls provider charm."""
    cert = (
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
    # Create a mock Certificate object with a raw attribute
    cert_mock = MagicMock()
    cert_mock.raw = cert
    cert_mock.__str__ = MagicMock(return_value=cert)  # type: ignore[method-assign]

    # Create CSR mock with common_name
    csr_mock = MagicMock()
    csr_mock.common_name = TEST_EXTERNAL_HOSTNAME_CONFIG

    provider_cert_mock = MagicMock()
    provider_cert_mock.certificate = cert_mock
    provider_cert_mock.certificate_signing_request = csr_mock
    provider_cert_mock.ca = cert_mock
    provider_cert_mock.chain = [
        cert_mock
    ]  # Chain should be list of Certificate objects with .raw attribute
    monkeypatch.setattr(
        (
            "charms.tls_certificates_interface.v4.tls_certificates"
            ".TLSCertificatesRequiresV4.get_provider_certificates"
        ),
        MagicMock(return_value=[provider_cert_mock]),
    )
    return cert


@pytest.fixture(scope="function", name="config")
def config_fixture() -> dict[str, str]:
    """Valid charm config fixture."""
    return {
        "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
        "gateway-class": GATEWAY_CLASS_CONFIG,
    }


@pytest.fixture(scope="function", name="client_with_mock_external")
def client_with_mock_external_fixture(
    mock_lightkube_client: MagicMock,
    gateway_class_resource: GenericGlobalResource,
    private_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> MagicMock:
    """Mock necessary external methods for the charm to work properly with harness."""
    mock_lightkube_client.list = MagicMock(return_value=[gateway_class_resource])
    mock_lightkube_client.get = MagicMock(
        return_value=GenericNamespacedResource(status={"addresses": [{"value": "10.0.0.0"}]}),
    )
    monkeypatch.setattr("ops.jujuversion.JujuVersion.has_secrets", PropertyMock(return_value=True))
    juju_secret_mock = MagicMock(spec=Secret)
    # In v4, the secret key name is "private-key" instead of "key"
    juju_secret_mock.get_content.return_value = {"private-key": private_key}
    monkeypatch.setattr("ops.model.Model.get_secret", MagicMock(return_value=juju_secret_mock))
    monkeypatch.setattr(
        "charms.traefik_k8s.v2.ingress.IngressPerAppProvider.publish_url",
        MagicMock(),
    )
    return mock_lightkube_client
