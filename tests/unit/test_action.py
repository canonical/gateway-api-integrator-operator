# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""

from unittest.mock import MagicMock

import ops
import ops.testing
import pytest
from ops.testing import Harness
from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG


def test_on_get_certificates_action(harness: Harness, monkeypatch: pytest.MonkeyPatch):
    """
    arrange: given a stock gateway-api-integrator charm.
    act: Add a relation to tls provider while config is invalid.
    assert: the charm stays in blocked state.
    """
    harness.begin()
    mock_relation_data = {
        harness.charm.app: {
            f"certificate-{TEST_EXTERNAL_HOSTNAME_CONFIG}": "mock certificate",
            f"ca-{TEST_EXTERNAL_HOSTNAME_CONFIG}": "mock certificate",
            f"chain-{TEST_EXTERNAL_HOSTNAME_CONFIG}": "mock certificate",
        }
    }

    tls_information_mock = MagicMock()
    tls_information_mock.tls_requirer_integration.data = mock_relation_data
    monkeypatch.setattr(
        "charm.TLSInformation.from_charm", MagicMock(return_value=tls_information_mock)
    )
    output = harness.run_action(
        "get-certificate", params={"hostname": TEST_EXTERNAL_HOSTNAME_CONFIG}
    )
    assert set(output.results.items()) == set(mock_relation_data[harness.charm.app].items())


def test_on_get_certificates_action_invalid_hostname(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
):
    """
    arrange: given a stock gateway-api-integrator charm.
    act: Add a relation to tls provider while config is invalid.
    assert: the charm stays in blocked state.
    """
    harness.begin()
    mock_relation_data_missing: dict = {harness.charm.app: {}}

    tls_information_mock = MagicMock()
    tls_information_mock.tls_requirer_integration.data = mock_relation_data_missing
    monkeypatch.setattr(
        "charm.TLSInformation.from_charm", MagicMock(return_value=tls_information_mock)
    )
    with pytest.raises(ops.testing.ActionFailed):
        harness.run_action("get-certificate", params={"hostname": TEST_EXTERNAL_HOSTNAME_CONFIG})
