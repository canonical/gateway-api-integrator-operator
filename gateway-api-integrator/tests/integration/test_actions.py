# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for actions."""

import jubilant
import pytest
from conftest import TEST_EXTERNAL_HOSTNAME_CONFIG


@pytest.mark.abort_on_fail
def test_get_certificate_action(
    juju: jubilant.Juju,
    configured_application_with_tls: str,
    ingress_requirer_application: str,
):
    """Deploy the charm with valid config and tls integration.

    Assert on valid output of get-certificate.
    """
    juju.integrate(
        configured_application_with_tls,
        f"{ingress_requirer_application}:ingress",
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, ingress_requirer_application
        ),
        error=jubilant.any_error,
    )

    result = juju.run(
        f"{configured_application_with_tls}/leader",
        "get-certificate",
        {"hostname": TEST_EXTERNAL_HOSTNAME_CONFIG},
    )
    assert "certificate" in result.results
    assert "ca" in result.results
    assert "chain" in result.results
    assert result.results["certificate"].startswith("-----BEGIN CERTIFICATE-----")
    assert result.results["ca"].startswith("-----BEGIN CERTIFICATE-----")
    assert result.results["chain"].startswith("-----BEGIN CERTIFICATE-----")
