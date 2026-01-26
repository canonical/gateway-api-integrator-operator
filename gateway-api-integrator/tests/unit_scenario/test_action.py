# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the charm action."""

from datetime import timedelta

import pytest
from charm import GatewayAPICharm
from charmlibs.interfaces.tls_certificates import (
    Certificate,
    CertificateRequestAttributes,
    CertificateSigningRequest,
    PrivateKey,
    ProviderCertificate,
)
from ops import testing

TEST_EXTERNAL_HOSTNAME_CONFIG = "www.gateway.internal"


# Generate real cryptographic objects for testing
def _generate_test_certificates():
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

    return str(cert), str(ca_cert), str(csr)


CERTIFICATE, CA_CERTIFICATE, CSR = _generate_test_certificates()


def test_get_certificate_action(
    base_state: dict,
    gateway_relation: testing.Relation,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    arrange: Mock TLSCertificatesRequiresV4 to return a certificate for the hostname.
    act: Run the get-certificate action.
    assert: The action returns the expected certificate.
    """
    # Create mock certificate objects
    csr = CertificateSigningRequest.from_string(CSR)
    cert = Certificate.from_string(CERTIFICATE)
    ca = Certificate.from_string(CA_CERTIFICATE)
    private_key = PrivateKey.generate()

    certificates_relation = testing.Relation(
        endpoint="certificates",
        interface="tls-certificates",
        remote_app_name="certificate-provider",
    )

    provider_certificate = ProviderCertificate(
        relation_id=certificates_relation.id,
        certificate=cert,
        ca=ca,
        chain=[ca],
        revoked=False,
        certificate_signing_request=csr,
    )

    # Mock the get_assigned_certificate method to return our certificate
    monkeypatch.setattr(
        "charms.tls_certificates_interface.v4.tls_certificates."
        + "TLSCertificatesRequiresV4.get_assigned_certificate",
        lambda self, certificate_request: (provider_certificate, private_key),
    )

    base_state["relations"].append(gateway_relation)
    base_state["relations"].append(certificates_relation)
    base_state["config"] = {
        "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
        "gateway-class": "cilium",
    }
    base_state["leader"] = True

    ctx = testing.Context(GatewayAPICharm)
    state = testing.State(**base_state)

    # Run the get-certificate action
    ctx.run(
        ctx.on.action("get-certificate", params={"hostname": TEST_EXTERNAL_HOSTNAME_CONFIG}), state
    )
    assert cert == ctx.action_results["certificate"]
    assert ca == ctx.action_results["ca"]
