# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Kubernetes and LXD model fixtures for cross-model DNS tests."""

import logging

import jubilant
import pytest

from tests.integration.conftest import JUJU_WAIT_TIMEOUT

logger = logging.getLogger(__name__)

BIND_APP_NAME = "bind"
BIND_BASE = "ubuntu@22.04"
BIND_CHANNEL = "latest/edge"
K8S_CONTROLLER = "concierge-k8s"
LXD_CONTROLLER = "concierge-lxd"


@pytest.fixture(scope="module", name="juju_k8s")
def juju_k8s_fixture(request: pytest.FixtureRequest):
    """Create a temporary model on the Concierge Kubernetes controller."""
    keep_models = bool(request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models, controller=K8S_CONTROLLER) as juju:
        juju.wait_timeout = JUJU_WAIT_TIMEOUT
        yield juju

        if request.session.testsfailed:
            logger.error(juju.debug_log(limit=1000))


@pytest.fixture(scope="module", name="juju")
def juju_fixture(juju_k8s: jubilant.Juju) -> jubilant.Juju:
    """Return the Kubernetes model for shared integration fixtures."""
    return juju_k8s


@pytest.fixture(scope="module", name="juju_lxd")
def juju_lxd_fixture(request: pytest.FixtureRequest):
    """Create a temporary model on the Concierge LXD controller."""
    keep_models = bool(request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models, controller=LXD_CONTROLLER) as juju:
        juju.wait_timeout = JUJU_WAIT_TIMEOUT
        yield juju

        if request.session.testsfailed:
            logger.error(juju.debug_log(limit=1000))


@pytest.fixture(scope="module", name="bind_operator")
def bind_operator_fixture(
    juju_lxd: jubilant.Juju,
    juju_k8s: jubilant.Juju,
    configured_application_with_tls: str,
    ingress_requirer_application: str,
) -> str:
    """Deploy Bind on LXD and relate its offer to the Kubernetes application."""
    juju_k8s.integrate(
        configured_application_with_tls,
        f"{ingress_requirer_application}:ingress",
    )
    juju_k8s.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, ingress_requirer_application
        ),
        error=jubilant.any_error,
    )
    juju_lxd.deploy(BIND_APP_NAME, app=BIND_APP_NAME, base=BIND_BASE, channel=BIND_CHANNEL)
    juju_lxd.wait(
        lambda status: jubilant.all_active(status, BIND_APP_NAME),
        error=jubilant.any_error,
    )
    juju_lxd.offer(BIND_APP_NAME, endpoint="dns-record")
    lxd_model = juju_lxd.show_model()
    juju_k8s.consume(
        f"{lxd_model.short_name}.{BIND_APP_NAME}",
        alias=BIND_APP_NAME,
        controller=lxd_model.controller_name,
        owner="admin",
    )
    juju_k8s.integrate(
        f"{configured_application_with_tls}:dns-record",
        f"{BIND_APP_NAME}:dns-record",
    )
    juju_k8s.wait(
        lambda status: jubilant.all_active(status, configured_application_with_tls),
        error=jubilant.any_error,
    )
    return BIND_APP_NAME
