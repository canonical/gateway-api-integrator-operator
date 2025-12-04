# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Disable protected access rules due to the need to test charm._ingress_provider
# pylint: disable=protected-access

"""Unit tests for ingress."""
from unittest.mock import MagicMock

import pytest
from ops.testing import Harness


@pytest.mark.usefixtures("client_with_mock_external")
def test_ingress_ipa_provided(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    arrange: Given a charm with mocked _reconcile method.
    act: Fire the ingress_data_provided event.
    assert: the charm correctly calls the _reconcile method.
    """
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


@pytest.mark.usefixtures("client_with_mock_external")
def test_ingress_ipa_removed(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    arrange: Given a charm with mocked _reconcile method.
    act: Fire the ingress_data_removed event.
    assert: the charm correctly calls the _reconcile method.
    """
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
