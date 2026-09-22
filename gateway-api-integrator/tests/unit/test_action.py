# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the charm action."""

import json

import pytest
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


@pytest.mark.parametrize(
    (
        "external_hostname",
        "enforce_https",
        "ingress_url",
        "expected_endpoints",
    ),
    [
        (
            TEST_EXTERNAL_HOSTNAME_CONFIG,
            True,
            "https://example.com/testing-model-testing-ingress-app",
            {
                "gateway-api-integrator": {"url": "https://example.com"},
                "remote": {"url": "https://example.com/testing-model-testing-ingress-app"},
            },
        ),
        (
            "",
            False,
            "http://1.2.3.4/testing-model-testing-ingress-app",
            {
                "gateway-api-integrator": {"url": "http://1.2.3.4"},
                "remote": {"url": "http://1.2.3.4/testing-model-testing-ingress-app"},
            },
        ),
    ],
)
def test_get_proxied_endpoints_action(
    base_state: dict,
    gateway_relation: testing.Relation,
    mock_certificates_relation_data: str,
    external_hostname: str,
    enforce_https: bool,
    ingress_url: str,
    expected_endpoints: dict,
) -> None:
    """
    arrange: Configure the gateway with an optional external hostname and a published ingress.
    act: Run the get-proxied-endpoints action.
    assert: The action returns the expected gateway and published ingress endpoints.
    """
    certificates_relation = testing.Relation(
        endpoint="certificates",
        interface="certificates",
        remote_app_name="certificate-provider",
        remote_app_data={"certificates": mock_certificates_relation_data},
    )
    gateway_relation.local_app_data.update({"ingress": json.dumps({"url": ingress_url})})
    base_state["relations"].append(gateway_relation)
    if external_hostname:
        base_state["relations"].append(certificates_relation)
    base_state["config"] = {
        "external-hostname": external_hostname,
        "enforce-https": enforce_https,
        "gateway-class": "cilium",
    }
    base_state["leader"] = True

    ctx = testing.Context(GatewayAPICharm)
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.config_changed(), state)
    # Run the get-proxied-endpoints action
    ctx.run(ctx.on.action("get-proxied-endpoints"), state)

    assert json.loads(ctx.action_results["proxied-endpoints"]) == expected_endpoints
