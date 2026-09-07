# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for certificates integration."""

import pytest
from ops import testing

from charm import GatewayAPICharm
from state.charm_state import CharmState, InvalidCharmConfigError, ProxyMode
from state.tls import TLSInformation, TlsIntegrationMissingError


@pytest.mark.usefixtures("client_with_mock_external")
def test_tls_information_integration_missing() -> None:
    """
    arrange: Given a charm with tls integration missing.
    act: Initialize TLSInformation state component.
    assert: TLSIntegrationMissingError is raised.
    """
    ctx = testing.Context(GatewayAPICharm)
    state_in = testing.State(leader=True)

    with ctx(ctx.on.update_status(), state_in) as manager:
        charm = manager.charm
        charm_state = CharmState(
            gateway_class_name="cilium",
            enforce_https=True,
            proxy_mode=ProxyMode.INGRESS,
            requires_ip_certificate=False,
            hsts_max_age=31536000,
            hostnames={"example.com"},
        )
        with pytest.raises(TlsIntegrationMissingError):
            TLSInformation.from_charm(
                charm,
                charm_state.hostnames,
                charm.certificates,
            )


@pytest.mark.usefixtures("client_with_mock_external")
def test_from_charm_parses_csr_subject_attributes(
    certificates_relation: testing.Relation,
) -> None:
    """CharmState should expose parsed CSR subject attributes from config."""
    ctx = testing.Context(GatewayAPICharm)
    state_in = testing.State(
        leader=True,
        config={
            "gateway-class": "cilium",
            "csr-subject-attributes": (
                "C=DE, ST=Hesse, L=Frankfurt, O=Canonical, OU=Engineering, "
                "CN=csr.example.com, emailAddress=ops@example.com"
            ),
        },
        relations=[certificates_relation],
    )

    with ctx(ctx.on.update_status(), state_in) as manager:
        charm = manager.charm
        charm_state = CharmState.from_charm_and_providers(
            charm,
            available_gateway_classes=["cilium"],
            ingress_provider=charm._ingress_provider,
            gateway_route_provider=charm._gateway_route_provider,
        )

        assert charm_state.csr_subject_attributes == {
            "country_name": "DE",
            "state_or_province_name": "Hesse",
            "locality_name": "Frankfurt",
            "organization": "Canonical",
            "organizational_unit": "Engineering",
            "common_name": "csr.example.com",
            "email_address": "ops@example.com",
        }


@pytest.mark.usefixtures("client_with_mock_external")
@pytest.mark.parametrize(
    "value",
    [
        pytest.param("foo=bar", id="unsupported-key"),
        pytest.param("C=DE,,O=Canonical", id="empty-pair"),
        pytest.param("C=DE,C=US", id="duplicate-key"),
        pytest.param("C=", id="empty-value"),
    ],
)
def test_from_charm_rejects_invalid_csr_subject_attributes(
    value: str,
    certificates_relation: testing.Relation,
) -> None:
    """CharmState should reject invalid csr-subject-attributes config values."""
    ctx = testing.Context(GatewayAPICharm)
    state_in = testing.State(
        leader=True,
        config={
            "gateway-class": "cilium",
            "csr-subject-attributes": value,
        },
        relations=[certificates_relation],
    )

    with ctx(ctx.on.update_status(), state_in) as manager:
        charm = manager.charm
        with pytest.raises(InvalidCharmConfigError, match='invalid "csr-subject-attributes"'):
            CharmState.from_charm_and_providers(
                charm,
                available_gateway_classes=["cilium"],
                ingress_provider=charm._ingress_provider,
                gateway_route_provider=charm._gateway_route_provider,
            )
