# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""

import ops
import pytest
from ops.testing import Harness
from unittest.mock import MagicMock
from .conftest import GATEWAY_CLASS_CONFIG, TEST_EXTERNAL_HOSTNAME_CONFIG
from lightkube.core.exceptions import ConfigError


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


def test_deploy_lightkube_error(
    harness: Harness, certificates_relation_data: dict, monkeypatch: pytest.MonkeyPatch
):
    """
    arrange: given a gateway-api-integrator charm with valid tls relation
    and mocked lightkube client.
    act: Change the charm's config to trigger reconciliation.
    assert: the charm goes into error state.
    """
    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    harness.begin()
    lightkube_get_sa_mock = MagicMock()
    lightkube_get_sa_mock.from_service_account = MagicMock(side_effect=ConfigError)
    monkeypatch.setattr("charm.KubeConfig", lightkube_get_sa_mock)

    with pytest.raises(RuntimeError):
        harness.update_config(
            {
                "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
                "gateway-class": GATEWAY_CLASS_CONFIG,
            }
        )


def test_deploy_with_initial_hooks(harness: Harness):
    """
    arrange: given a gateway-api-integrator charm with valid tls relation
    and mocked lightkube client.
    act: Change the charm's config to trigger reconciliation.
    assert: the charm goes into error state.
    """
    harness.begin_with_initial_hooks()
