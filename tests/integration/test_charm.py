# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for charm deploy."""

import logging

import lightkube
import pytest
from juju.application import Application
from lightkube.generic_resource import create_namespaced_resource
from pytest_operator.plugin import OpsTest
from requests import Session

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG
from .helper import DNSResolverHTTPSAdapter, get_ingress_url_for_application

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
    ops_test: OpsTest,
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

    ingress_url = await get_ingress_url_for_application(ingress_requirer_application, ops_test)
    assert ingress_url.netloc == TEST_EXTERNAL_HOSTNAME_CONFIG
    assert ingress_url.path == f"/{application.model.name}-{ingress_requirer_application.name}"

    session = Session()
    session.mount("https://", DNSResolverHTTPSAdapter(ingress_url.netloc, gateway_lb_ip))

    res = session.get(
        f"http://{gateway_lb_ip}{ingress_url.path}",
        headers={"Host": ingress_url.netloc},
        verify=False,  # nosec - calling charm ingress URL
        allow_redirects=False,
        timeout=30,
    )
    assert res.status_code == 301

    assert res.headers["location"] == f"https://{ingress_url.netloc}:443{ingress_url.path}"
    res = session.get(
        f"http://{gateway_lb_ip}/invalid",
        headers={"Host": ingress_url.netloc},
        verify=False,  # nosec - calling charm ingress URL
        timeout=30,
    )
    assert res.status_code == 404

    res = session.get(
        f"http://{gateway_lb_ip}{ingress_url.path}",
        headers={"Host": ingress_url.netloc},
        verify=False,  # nosec - calling charm ingress URL
        timeout=30,
    )
    assert "Welcome to flask-k8s Charm" in str(res.content)
