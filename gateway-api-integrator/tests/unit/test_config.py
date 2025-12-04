# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm config."""

import pytest
from ops.testing import Harness
from state.config import InvalidCharmConfigError


@pytest.mark.usefixtures("client_with_mock_external")
def test_config(harness: Harness):
    """
    arrange: Given a charm with unavailable gateway class/invalid config.
    act: Initialize the CharmConfig state component.
    assert: InvalidCharmConfigError is raised in both cases.
    """
    harness.update_config(
        {
            "gateway-class": "not-available",
        }
    )
    with pytest.raises(InvalidCharmConfigError):
        harness.begin()
