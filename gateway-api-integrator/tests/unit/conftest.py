# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for gateway-api-integrator charm unit tests."""

import json
from datetime import timedelta
from unittest.mock import MagicMock, PropertyMock

import pytest
from charmlibs.interfaces.tls_certificates import (
    Certificate,
    CertificateRequestAttributes,
    CertificateSigningRequest,
    PrivateKey,
)
from lightkube.core.client import Client
from lightkube.generic_resource import GenericGlobalResource, GenericNamespacedResource
from lightkube.models.meta_v1 import ObjectMeta
from ops import testing

TEST_EXTERNAL_HOSTNAME_CONFIG = "example.com"
GATEWAY_CLASS_CONFIG = "cilium"


@pytest.fixture(scope="module", name="mock_certificates_relation_data")
def mock_certificates_relation_data_fixture() -> str:
    """Generate valid certificate objects for testing."""
    # Generate CA
    ca_private_key = PrivateKey.generate()
    ca_attributes = CertificateRequestAttributes(
        common_name="Test CA",
    )
    ca_cert = Certificate.generate_self_signed_ca(
        attributes=ca_attributes, private_key=ca_private_key, validity=timedelta(days=365)
    )

    # Generate CSR and certificate
    csr_private_key = PrivateKey.generate()
    csr_attributes = CertificateRequestAttributes(
        common_name=TEST_EXTERNAL_HOSTNAME_CONFIG,
    )
    csr = CertificateSigningRequest.generate(csr_attributes, csr_private_key)
    cert = Certificate.generate(
        csr=csr, ca=ca_cert, ca_private_key=ca_private_key, validity=timedelta(days=365)
    )

    return json.dumps(
        [
            {
                "certificate": str(cert),
                "certificate_signing_request": str(csr),
                "ca": str(ca_cert),
                "chain": [str(ca_cert), str(cert)],
            }
        ]
    )


@pytest.fixture(scope="function", name="base_state")
def base_state_fixture(monkeypatch: pytest.MonkeyPatch):
    """Mock the base state for the charm."""
    monkeypatch.setattr("client.KubeConfig", MagicMock())
    monkeypatch.setattr("client.Client", MagicMock())
    monkeypatch.setattr(
        "charm.GatewayAPICharm.available_gateway_classes",
        lambda self: [GATEWAY_CLASS_CONFIG],
    )
    monkeypatch.setattr("charm.GatewayAPICharm._define_secret_resources", MagicMock())
    monkeypatch.setattr(
        "charm.GatewayAPICharm._define_ingress_resources_and_publish_url", MagicMock()
    )
    monkeypatch.setattr("charm.GatewayAPICharm._set_status_gateway_address", MagicMock())
    monkeypatch.setattr("charm.GatewayResourceManager.current_gateway_resource", MagicMock())
    monkeypatch.setattr(
        "charm.GatewayResourceManager.gateway_address", lambda self, name: "1.2.3.4"
    )
    monkeypatch.setattr("charm.HTTPRouteResourceManager.cleanup_resources", MagicMock())
    monkeypatch.setattr("charm.ServiceResourceManager.cleanup_resources", MagicMock())

    dns_relation = testing.Relation(
        endpoint="dns-record",
        interface="dns_record",
    )

    return {
        "leader": True,
        "config": {
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        },
        "relations": [
            dns_relation,
        ],
        "model": testing.Model(
            name="testmodel",
        ),
    }


@pytest.fixture(scope="function", name="certificates_relation")
def certificates_relation_fixture(mock_certificates_relation_data: str):
    """Return a mock certificates relation data."""
    return testing.Relation(
        endpoint="certificates",
        interface="certificates",
        remote_app_data={"certificates": mock_certificates_relation_data},
    )


@pytest.fixture(scope="function", name="gateway_relation")
def gateway_relation_fixture():
    """Return a mock gateway relation data."""
    return testing.Relation(
        endpoint="gateway",
        interface="ingress",
        remote_app_data={
            "model": '"testing-model"',
            "name": '"testing-ingress-app"',
            "port": "8080",
        },
        remote_units_data={
            0: {"host": '"testing-host.example.com"'},
        },
    )


@pytest.fixture(scope="function", name="gateway_route_relation")
def gateway_route_relation_fixture():
    """Return a mock gateway-route v1 relation data."""
    return testing.Relation(
        endpoint="gateway-route",
        interface="gateway-route",
        remote_app_data={
            "hostname": json.dumps("example.com"),
            "additional_hostnames": json.dumps([]),
        },
    )


@pytest.fixture(scope="function", name="gateway_class_resource")
def gateway_class_resource_fixture() -> GenericGlobalResource:
    """Mock gateway class global resource."""
    return GenericGlobalResource(metadata=ObjectMeta(name=GATEWAY_CLASS_CONFIG))


@pytest.fixture(scope="function", name="mock_lightkube_client")
def mock_lightkube_client_fixture(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock the lightkube client returned by charm.get_client."""
    lightkube_client_mock = MagicMock(spec=Client)
    monkeypatch.setattr("charm.get_client", MagicMock(return_value=lightkube_client_mock))
    return lightkube_client_mock


@pytest.fixture(scope="function", name="client_with_mock_external")
def client_with_mock_external_fixture(
    mock_lightkube_client: MagicMock,
    gateway_class_resource: GenericGlobalResource,
    monkeypatch: pytest.MonkeyPatch,
) -> MagicMock:
    """Mock external methods so the charm reconcile can run with a real charm state."""
    mock_lightkube_client.list = MagicMock(return_value=[gateway_class_resource])
    mock_lightkube_client.get = MagicMock(
        return_value=GenericNamespacedResource(status={"addresses": [{"value": "10.0.0.0"}]}),
    )
    monkeypatch.setattr("ops.jujuversion.JujuVersion.has_secrets", PropertyMock(return_value=True))
    monkeypatch.setattr(
        "charms.traefik_k8s.v2.ingress.IngressPerAppProvider.publish_url",
        MagicMock(),
    )
    return mock_lightkube_client
