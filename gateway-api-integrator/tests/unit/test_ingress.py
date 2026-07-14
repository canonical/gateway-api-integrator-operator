# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for ingress."""

from unittest.mock import MagicMock

import pytest
from ops import testing

from charm import GatewayAPICharm


@pytest.mark.usefixtures("client_with_mock_external")
def test_ingress_ipa_provided(
    gateway_relation: testing.Relation,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    arrange: given a charm with a mocked _reconcile method and an ingress requirer.
    act: run the gateway relation-changed event (fires the data-provided event).
    assert: the charm calls the _reconcile method.
    """
    reconcile_mock = MagicMock()
    monkeypatch.setattr("charm.GatewayAPICharm._reconcile", reconcile_mock)
    ctx = testing.Context(GatewayAPICharm)
    state_in = testing.State(leader=True, relations=[gateway_relation])

    ctx.run(ctx.on.relation_changed(gateway_relation), state_in)

    reconcile_mock.assert_called_once()


@pytest.mark.usefixtures("client_with_mock_external")
def test_ingress_ipa_removed(
    gateway_relation: testing.Relation,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    arrange: given a charm with a mocked _reconcile method and an ingress requirer.
    act: run the gateway relation-broken event (fires the data-removed event).
    assert: the charm calls the _reconcile method.
    """
    reconcile_mock = MagicMock()
    monkeypatch.setattr("charm.GatewayAPICharm._reconcile", reconcile_mock)
    ctx = testing.Context(GatewayAPICharm)
    state_in = testing.State(leader=True, relations=[gateway_relation])

    ctx.run(ctx.on.relation_broken(gateway_relation), state_in)

    reconcile_mock.assert_called_once()
