# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""

import ops
import ops.testing
import pytest
from ops.testing import Harness

from .conftest import GATEWAY_CLASS_CONFIG, TEST_EXTERNAL_HOSTNAME_CONFIG


@pytest.mark.usefixtures("client_with_mock_external")
def test_on_get_certificates_action(harness: Harness, certificates_relation_data: dict[str, str]):
    """
    arrange: given a stock gateway-api-integrator charm.
    act: Add a relation to tls provider while config is invalid.
    assert: the charm stays in blocked state.
    """
    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    harness.begin()
    output = harness.run_action(
        "get-certificate", params={"hostname": TEST_EXTERNAL_HOSTNAME_CONFIG}
    )
    assert (
        output.results["certificate"]
        == certificates_relation_data[f"certificate-{TEST_EXTERNAL_HOSTNAME_CONFIG}"]
    )


@pytest.mark.usefixtures("client_with_mock_external")
def test_on_get_certificates_action_invalid_hostname(
    harness: Harness, certificates_relation_data: dict[str, str]
):
    """
    arrange: given a stock gateway-api-integrator charm.
    act: Add a relation to tls provider while config is invalid.
    assert: the charm stays in blocked state.
    """
    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    harness.begin()
    with pytest.raises(ops.testing.ActionFailed):
        harness.run_action("get-certificate", params={"hostname": "invalid-hostname"})
