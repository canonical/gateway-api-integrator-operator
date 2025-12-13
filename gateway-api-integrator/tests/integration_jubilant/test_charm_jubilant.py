# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests using Jubilant the charm."""

import json
import subprocess  # nosec

import jubilant


def test_deploy_charm(juju: jubilant.Juju, gateway_app: str, external_hostname: str):
    """
    Test that the charm correctly sets up the DNS record relation.
    Deploy any-charm and integrate it on dns-record relation.
    Assert that the relation data contains the expected DNS entries.
    """
    # Deploy any-charm that provides the dns-record relation
    juju.deploy(
        "any-charm",
        channel="latest/beta",
    )
    juju.integrate(f"{gateway_app}:dns-record", "any-charm")
    juju.wait(jubilant.all_active)

    # Assert that the dns-record is in the relation data
    unit_info_str = juju.cli("show-unit", "any-charm/0", "--format", "json")
    unit_info_dict = json.loads(unit_info_str)["any-charm/0"]
    for relation in unit_info_dict["relation-info"]:
        if relation["endpoint"] == "provide-dns-record":
            dns_record = json.loads(relation["application-data"]["dns_entries"])[0]
            assert dns_record["domain"] == external_hostname
            assert dns_record["host_label"] == "@"
            assert "record_data" in dns_record
            assert "uuid" in dns_record
            break

    juju.remove_relation(gateway_app, "flask-k8s")
    juju.wait(lambda status: jubilant.all_blocked(status, gateway_app))
    cmd = (
        "kubectl -n gateway get all,httproute,service "
        f"--selector gateway-api-integrator.charm.juju.is/managed-by={gateway_app} | wc -l"
    )
    output = subprocess.check_output(["/bin/bash", "-c", cmd], stderr=subprocess.STDOUT)  # nosec
    assert "No resources found" in str(output)
