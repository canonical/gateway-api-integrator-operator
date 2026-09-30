# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the cross-model DNS record relation."""

import subprocess  # nosec: B404

import jubilant
import lightkube
import tenacity
from jubilant.statustypes import UnitStatus

from tests.integration.conftest import TEST_EXTERNAL_HOSTNAME_CONFIG
from tests.integration.helper import get_gateway_resource


def _unit_address(unit: UnitStatus) -> str:
    """Return a reachable unit address from Juju status."""
    return unit.address or unit.public_address


def _dig(nameserver: str, hostname: str) -> str:
    """Resolve an A record through a specific nameserver from the test host."""
    result = subprocess.run(  # nosec: B603 B607
        ["dig", "+short", f"@{nameserver}", hostname, "A"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _assert_resolves(
    juju_lxd: jubilant.Juju,
    bind_operator: str,
    hostname: str,
    expected_address: str,
) -> None:
    """Retry until Bind resolves a hostname to the expected address."""
    for attempt in tenacity.Retrying(
        stop=tenacity.stop_after_delay(120),
        wait=tenacity.wait_fixed(5),
        reraise=True,
    ):
        with attempt:
            bind_units = juju_lxd.status().apps[bind_operator].units
            answers = (_dig(_unit_address(unit), hostname) for unit in bind_units.values())
            assert any(expected_address in answer.splitlines() for answer in answers)


def test_dns_record_resolves_via_bind(
    juju_lxd: jubilant.Juju,
    configured_application_with_tls: str,
    bind_operator: str,
    lightkube_client: lightkube.Client,
) -> None:
    """Bind should resolve the configured hostname to the Gateway address."""
    gateway = get_gateway_resource(lightkube_client, configured_application_with_tls)
    gateway_address = gateway.status["addresses"][0]["value"]  # type: ignore

    _assert_resolves(juju_lxd, bind_operator, TEST_EXTERNAL_HOSTNAME_CONFIG, gateway_address)


def test_dns_record_updates_on_hostname_change(
    juju_k8s: jubilant.Juju,
    juju_lxd: jubilant.Juju,
    configured_application_with_tls: str,
    bind_operator: str,
    lightkube_client: lightkube.Client,
) -> None:
    """Bind should resolve a replacement external hostname."""
    new_hostname = "gateway-new.internal"
    juju_k8s.config(configured_application_with_tls, {"external-hostname": new_hostname})
    juju_k8s.wait(
        lambda status: jubilant.all_active(status, configured_application_with_tls),
        error=jubilant.any_error,
    )
    gateway = get_gateway_resource(lightkube_client, configured_application_with_tls)
    gateway_address = gateway.status["addresses"][0]["value"]  # type: ignore

    _assert_resolves(juju_lxd, bind_operator, new_hostname, gateway_address)


def test_dns_record_relation_removal_keeps_charm_active(
    juju_k8s: jubilant.Juju,
    configured_application_with_tls: str,
    bind_operator: str,
) -> None:
    """Removing the optional DNS relation should leave the charm active."""
    juju_k8s.remove_relation(
        f"{configured_application_with_tls}:dns-record",
        f"{bind_operator}:dns-record",
    )
    juju_k8s.wait(
        lambda status: "dns-record" not in status.apps[configured_application_with_tls].relations,
        error=jubilant.any_error,
    )
    juju_k8s.wait(
        lambda status: status.apps[configured_application_with_tls].is_active,
        error=jubilant.any_error,
    )
