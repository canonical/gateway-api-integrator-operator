# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for ingress."""
from unittest.mock import MagicMock

import pytest
from ops.testing import Harness
from ops.model import Relation


def test_ingress_ipa_provided(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
):
    reconcile_mock = MagicMock()
    monkeypatch.setattr("charm.GatewayAPICharm._reconcile", reconcile_mock)
    relation_id = harness.add_relation(
        "gateway",
        "test-charm",
    )
    harness.begin()
    harness.charm._ingress_provider.on.data_provided.emit(  # type: ignore
        harness.model.get_relation("gateway", relation_id),
        harness.model.app.name,
        harness.model.name,
        [],
        False,
        False,
    )
    reconcile_mock.assert_called_once()


def test_ingress_ipa_removed(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
):
    reconcile_mock = MagicMock()
    monkeypatch.setattr("charm.GatewayAPICharm._reconcile", reconcile_mock)
    relation_id = harness.add_relation(
        "gateway",
        "test-charm",
    )
    harness.begin()

    harness.charm._ingress_provider.on.data_removed.emit(
        harness.model.get_relation("gateway", relation_id)
    )
    reconcile_mock.assert_called_once()
