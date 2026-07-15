# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for certificates integration."""

import pytest
from ops import testing

from charm import GatewayAPICharm
from state.charm_state import CharmState, ProxyMode
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
            hostnames={"example.com"},
        )
        with pytest.raises(TlsIntegrationMissingError):
            TLSInformation.from_charm(
                charm,
                charm_state.hostnames,
                charm.certificates,
            )
