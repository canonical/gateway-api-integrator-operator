# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for charm deploy."""

import logging

import lightkube
import pytest
import requests
from juju.application import Application
from lightkube.generic_resource import create_namespaced_resource

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG

logger = logging.getLogger(__name__)
CUSTOM_RESOURCE_GROUP_NAME = "gateway.networking.k8s.io"
GATEWAY_RESOURCE_NAME = "Gateway"
GATEWAY_PLURAL = "gateways"
CREATED_BY_LABEL = "gateway-api-integrator.charm.juju.is/managed-by"


@pytest.mark.abort_on_fail
async def test_deploy(
    configured_application_with_tls: Application,
    ingress_requirer_application: Application,
    lightkube_client: lightkube.Client,
):
    """Deploy the charm together with related charms.

    Assert on the unit status before any relations/configurations take place.
    """
    application = configured_application_with_tls
    await application.model.add_relation(
        application.name, f"{ingress_requirer_application.name}:ingress"
    )
    await application.model.wait_for_idle(
        apps=[ingress_requirer_application.name, application.name],
        idle_period=30,
        status="active",
    )

    action = await application.units[0].run_action(
        "get-certificate", hostname=TEST_EXTERNAL_HOSTNAME_CONFIG
    )
    await action.wait()
    assert action.results

    gateway_generic_resource_class = create_namespaced_resource(
        CUSTOM_RESOURCE_GROUP_NAME, "v1", GATEWAY_RESOURCE_NAME, GATEWAY_PLURAL
    )
    gateway = lightkube_client.get(gateway_generic_resource_class, name=application.name)
    gateway_lb_ip = gateway.status["addresses"][0]["value"]  # type: ignore
    assert gateway_lb_ip, "LB address not assigned to gateway"

    ingress_url = (
        f"http://{gateway_lb_ip}/{application.model.name}-{ingress_requirer_application.name}"
    )
    res = requests.get(
        ingress_url,
        headers={"Host": TEST_EXTERNAL_HOSTNAME_CONFIG},
        verify=False,  # nosec - calling charm ingress URL
        timeout=30,
    )
    assert "Authentication required" in str(res.content)

    res = requests.get(
        f"http://{gateway_lb_ip}/invalid",
        headers={"Host": TEST_EXTERNAL_HOSTNAME_CONFIG},
        verify=False,  # nosec - calling charm ingress URL
        timeout=30,
    )
    assert res.status_code == 404

    res = requests.get(
        ingress_url,
        headers={"Host": TEST_EXTERNAL_HOSTNAME_CONFIG},
        verify=False,  # nosec - calling charm ingress URL
        allow_redirects=False,
        timeout=30,
    )
    assert res.status_code == 301
    assert res.headers["location"] == (
        f"https://{TEST_EXTERNAL_HOSTNAME_CONFIG}:443"
        f"/{application.model.name}-{ingress_requirer_application.name}",
    )
