# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import jubilant
import pytest


def test_dns_record_relation(juju: jubilant.Juju, app: str):
    """
    Test that the charm correctly sets up the DNS record relation.
    Deploy any-charm and integrate it on dns-record relation.
    Assert that the relation data contains the expected DNS entries.
    """
    juju.deploy(
        "any-charm",
        channel="latest/edge",
    )
    juju.integrate(f"{app}:dns-record", "any-charm")
    juju.wait(jubilant.all_active)

    # TODO: Replace below with actual command and assert relation data
    relation_data = juju.cli("xxxx")
