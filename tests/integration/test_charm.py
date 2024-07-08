# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for certificates relation."""

import logging

import lightkube
import pytest
from juju.application import Application
from lightkube.generic_resource import create_namespaced_resource
from lightkube.resources.core_v1 import Secret

logger = logging.getLogger(__name__)
TEST_EXTERNAL_HOSTNAME_CONFIG = "gateway.internal"
GATEWAY_CLASS_CONFIG = "cilium"
CUSTOM_RESOURCE_GROUP_NAME = "gateway.networking.k8s.io"
GATEWAY_RESOURCE_NAME = "Gateway"
GATEWAY_PLURAL = "gateways"
CREATED_BY_LABEL = "gateway-api-integrator.charm.juju.is/managed-by"


@pytest.mark.abort_on_fail
async def test_deploy(
    application: Application,
    certificate_provider_application: Application,
    ingress_requirer_application: Application,
    lightkube_client: lightkube.Client,
):
    """Deploy the charm together with related charms.

    Assert on the unit status before any relations/configurations take place.
    """
    await application.set_config(
        {"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG, "gateway-class": GATEWAY_CLASS_CONFIG}
    )
    await application.model.add_relation(application.name, certificate_provider_application.name)
    await application.model.wait_for_idle(
        apps=[certificate_provider_application.name],
        idle_period=30,
        status="active",
    )

    await application.model.add_relation(
        application.name, f"{ingress_requirer_application.name}:ingress"
    )
    await application.model.wait_for_idle(
        apps=[ingress_requirer_application.name],
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
    assert len(gateway.spec["listeners"]) == 2
    secret: Secret = lightkube_client.get(
        Secret, name=f"{application.name}-secret-{TEST_EXTERNAL_HOSTNAME_CONFIG}"
    )
    assert secret.data
    assert secret.data["tls.crt"]
    assert secret.data["tls.key"]

    gateway_address = gateway.status["addresses"][0]["value"]
    assert gateway_address
