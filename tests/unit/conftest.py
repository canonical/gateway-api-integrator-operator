# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for gateway-api-integrator charm unit tests."""

from unittest.mock import MagicMock, PropertyMock

import pytest
from lightkube.core.client import Client
from lightkube.generic_resource import GenericGlobalResource, GenericNamespacedResource
from lightkube.models.meta_v1 import ObjectMeta
from ops.model import Secret
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


@pytest.fixture(scope="function", name="gateway_relation_application_data")
def gateway_relation_application_data_fixture() -> dict[str, str]:
    """Mock gateway relation application data."""
    return {
        "name": '"gateway-api-integrator"',
        "model": '"testing"',
        "port": "8080",
        "strip_prefix": "false",
        "redirect_https": "false",
    }


@pytest.fixture(scope="function", name="gateway_relation_unit_data")
def gateway_relation_unit_data_fixture() -> dict[str, str]:
    """Mock gateway relation unit data."""
    return {"host": '"testing.ingress"', "ip": '"10.0.0.1"'}


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


@pytest.fixture(scope="function", name="private_key_and_password")
def private_key_and_password_fixture(harness: Harness) -> tuple[str, str]:
    """Mock private key juju secret."""
    tls = TLSRelationService(harness.model, MagicMock())
    password = tls.generate_password().encode()
    private_key = generate_private_key(password=password)
    return (password.decode(), private_key.decode())


@pytest.fixture(scope="function", name="juju_secret_mock")
def juju_secret_mock_fixture(
    monkeypatch: pytest.MonkeyPatch,
    private_key_and_password: tuple[str, str],
) -> tuple[str, str]:
    """Mock certificates integration."""
    password, private_key = private_key_and_password
    juju_secret_mock = MagicMock(spec=Secret)
    juju_secret_mock.get_content.return_value = {"key": private_key, "password": password}
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
    provider_cert_mock = MagicMock()
    provider_cert_mock.certificate = cert
    monkeypatch.setattr(
        (
            "charms.tls_certificates_interface.v3.tls_certificates"
            ".TLSCertificatesRequiresV3.get_provider_certificates"
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
    private_key_and_password: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> MagicMock:
    """Mock necessary external methods for the charm to work properly with harness."""
    mock_lightkube_client.list = MagicMock(return_value=[gateway_class_resource])
    mock_lightkube_client.get = MagicMock(
        return_value=GenericNamespacedResource(status={"addresses": [{"value": "10.0.0.0"}]}),
    )
    monkeypatch.setattr("ops.jujuversion.JujuVersion.has_secrets", PropertyMock(return_value=True))
    password, private_key = private_key_and_password
    juju_secret_mock = MagicMock(spec=Secret)
    juju_secret_mock.get_content.return_value = {"key": private_key, "password": password}
    monkeypatch.setattr("ops.model.Model.get_secret", MagicMock(return_value=juju_secret_mock))
    monkeypatch.setattr(
        "charms.traefik_k8s.v2.ingress.IngressPerAppProvider.publish_url",
        MagicMock(),
    )
    return mock_lightkube_client
