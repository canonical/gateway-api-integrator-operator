# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for actions."""

import pytest
from conftest import TEST_EXTERNAL_HOSTNAME_CONFIG
from juju.application import Application


@pytest.mark.abort_on_fail
async def test_get_certificate_action(
    configured_application_with_tls: Application,
    ingress_requirer_application: Application,
):
    """Deploy the charm with valid config and tls integration.

    Assert on valid output of get-certificate.
    """
    await configured_application_with_tls.model.add_relation(
        configured_application_with_tls.name,
        f"{ingress_requirer_application.name}:ingress",
    )
    await configured_application_with_tls.model.wait_for_idle(
        apps=[configured_application_with_tls.name, ingress_requirer_application.name],
        idle_period=30,
        status="active",
    )

    action = await configured_application_with_tls.units[0].run_action(
        "get-certificate", hostname=TEST_EXTERNAL_HOSTNAME_CONFIG
    )
    await action.wait()
    assert "certificate" in action.results
    assert "ca" in action.results
    assert "chain" in action.results
    assert action.results["certificate"].startswith("-----BEGIN CERTIFICATE-----")
    assert action.results["ca"].startswith("-----BEGIN CERTIFICATE-----")
    assert action.results["chain"].startswith("-----BEGIN CERTIFICATE-----")
