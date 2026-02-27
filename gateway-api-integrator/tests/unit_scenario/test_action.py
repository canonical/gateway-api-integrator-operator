# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the charm action."""

import json

from ops import testing

from charm import GatewayAPICharm

TEST_EXTERNAL_HOSTNAME_CONFIG = "example.com"


def test_get_certificate_action(
    base_state: dict,
    gateway_relation: testing.Relation,
    mock_certificates_relation_data: str,
) -> None:
    """
    arrange: Mock TLSCertificatesRequiresV4 to return a certificate for the hostname.
    act: Run the get-certificate action.
    assert: The action returns the expected certificate.
    """
    certificates_relation = testing.Relation(
        endpoint="certificates",
        interface="certificates",
        remote_app_name="certificate-provider",
        remote_app_data={"certificates": mock_certificates_relation_data},
    )

    base_state["relations"].append(gateway_relation)
    base_state["relations"].append(certificates_relation)
    base_state["config"] = {
        "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
        "gateway-class": "cilium",
    }
    base_state["leader"] = True

    ctx = testing.Context(GatewayAPICharm)
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.config_changed(), state)
    # Run the get-certificate action
    ctx.run(
        ctx.on.action("get-certificate", params={"hostname": TEST_EXTERNAL_HOSTNAME_CONFIG}), state
    )
    assert (
        ctx.action_results["certificate"]
        == json.loads(mock_certificates_relation_data)[0]["certificate"]
    )
    assert ctx.action_results["ca"] == json.loads(mock_certificates_relation_data)[0]["ca"]
