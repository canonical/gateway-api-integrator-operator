# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for certificates integration."""


import pytest
from ops.testing import Harness
from state.tls import TLSInformation, TlsIntegrationMissingError


@pytest.mark.usefixtures("client_with_mock_external")
def test_tls_information_integration_missing(harness: Harness):
    """
    arrange: Given a charm with tls integration missing.
    act: Initialize TLSInformation state component.
    assert: TLSIntegrationMissingError is raised.
    """
    harness.begin()
    with pytest.raises(TlsIntegrationMissingError):
        TLSInformation.from_charm(harness.charm, harness.charm.certificates)
