# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for gateway-api-integrator charm unit tests."""

import json
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from charms.tls_certificates_interface.v4.tls_certificates import (
    Certificate,
    CertificateRequestAttributes,
    CertificateSigningRequest,
    PrivateKey,
)
from ops import testing

from state.config import CharmConfig, ProxyMode

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
        "charm.CharmConfig.from_charm_and_providers",
        MagicMock(
            return_value=CharmConfig(
                gateway_class_name=GATEWAY_CLASS_CONFIG,
                hostname=TEST_EXTERNAL_HOSTNAME_CONFIG,
                enforce_https=True,
                proxy_mode=ProxyMode.DEFAULT,
            )
        ),
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

    dns_relation = testing.Relation(
        endpoint="dns-record",
        interface="dns_record",
    )

    yield {
        "leader": True,
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
    """Return a mock gateway-route relation data."""
    return testing.Relation(
        endpoint="gateway-route",
        interface="gateway_route",
        remote_app_data={
            "model": '"testing-model"',
            "name": '"testing-gateway-route-app"',
            "port": "8080",
            "hostname": '"example.com"',
            "paths": "[]",
        },
    )
