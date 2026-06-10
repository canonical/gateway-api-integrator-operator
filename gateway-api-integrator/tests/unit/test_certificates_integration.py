# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for certificates integration."""

import pytest
from ops.testing import Harness

from state.config import CharmConfig, ProxyMode
from state.tls import TLSInformation, TlsIntegrationMissingError


@pytest.mark.usefixtures("client_with_mock_external")
def test_tls_information_integration_missing(harness: Harness):
    """
    arrange: Given a charm with tls integration missing.
    act: Initialize TLSInformation state component.
    assert: TLSIntegrationMissingError is raised.
    """
    harness.begin()
    config = CharmConfig(
        gateway_class_name="cilium",
        hostnames={"example.com"},
        enforce_https=True,
        proxy_mode=ProxyMode.INGRESS,
        requires_ip_certificate=False,
    )
    with pytest.raises(TlsIntegrationMissingError):
        TLSInformation.from_charm(
            harness.charm,
            config,
            harness.charm.certificates,
        )
