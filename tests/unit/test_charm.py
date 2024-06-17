# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""

import ops
from ops.testing import Harness

from .conftest import GATEWAY_CLASS_CONFIG, TEST_EXTERNAL_HOSTNAME_CONFIG


def test_deploy_invalid_config(harness: Harness, certificates_relation_data: dict):
    """
    arrange: given a stock gateway-api-integrator charm.
    act: Add a relation to tls provider while config is invalid.
    assert: the charm stays in blocked state.
    """
    harness.begin()

    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )

    assert harness.charm.unit.status.name == ops.BlockedStatus.name


def test_deploy_missing_tls(harness: Harness):
    """
    arrange: given a stock gateway-api-integrator charm.
    act: Change the charm's config while tls is not ready.
    assert: the charm stays in blocked state.
    """
    harness.begin()

    harness.update_config(
        {"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG, "gateway-class": GATEWAY_CLASS_CONFIG}
    )

    assert harness.charm.unit.status.name == ops.BlockedStatus.name
