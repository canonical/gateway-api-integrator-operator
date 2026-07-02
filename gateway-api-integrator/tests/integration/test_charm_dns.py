# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for DNS record relation."""

import json
import subprocess  # nosec

import jubilant
from conftest import INGRESS_REQUIRER_APP_NAME, TEST_EXTERNAL_HOSTNAME_CONFIG


def test_dns_record_relation(
    juju: jubilant.Juju,
    configured_application_with_tls: str,
    ingress_requirer_application: str,
):
    """
    Test that the charm correctly sets up the DNS record relation.

    Deploy any-charm and integrate it on dns-record relation.
    Assert that the relation data contains the expected DNS entries.
    """
    gateway_app = configured_application_with_tls

    juju.integrate(gateway_app, f"{ingress_requirer_application}:ingress")
    juju.wait(
        lambda status: jubilant.all_active(status, gateway_app, ingress_requirer_application),
        timeout=600,
    )

    # Deploy any-charm that provides the dns-record relation
    juju.deploy(
        "any-charm",
        channel="latest/beta",
    )
    juju.integrate(f"{gateway_app}:dns-record", "any-charm")
    juju.wait(jubilant.all_active)

    # Assert that the dns-record is in the relation data
    if juju.version().major >= 4:
        unit_info_str = juju.cli("show-unit", f"{configured_application_with_tls}/0", "--format", "json")
    else:
        unit_info_str = juju.cli("show-unit", "any-charm/0", "--format", "json")
    unit_info_dict = json.loads(unit_info_str)["any-charm/0"]
    for relation in unit_info_dict["relation-info"]:
        if relation["endpoint"] == "provide-dns-record":
            dns_record = json.loads(relation["application-data"]["dns_entries"])[0]
            assert dns_record["domain"] == TEST_EXTERNAL_HOSTNAME_CONFIG
            assert dns_record["host_label"] == "@"
            assert "record_data" in dns_record
            assert "uuid" in dns_record
            break

    juju.remove_relation(gateway_app, INGRESS_REQUIRER_APP_NAME)
    juju.wait(lambda status: jubilant.all_active(status, gateway_app))
    model_name = juju.show_model().short_name
    cmd = (
        f"kubectl -n {model_name} get all,httproute,service "
        f"--selector gateway-api-integrator.charm.juju.is/managed-by={gateway_app} | wc -l"
    )
    output = subprocess.check_output(["/bin/bash", "-c", cmd], stderr=subprocess.STDOUT)  # nosec
    assert "No resources found" in str(output)
