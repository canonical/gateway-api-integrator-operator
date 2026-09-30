# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for cross-model DNS integration tests."""

import logging

import jubilant
import lightkube
import pytest

logger = logging.getLogger(__name__)

GATEWAY_APP_NAME = "gateway-api-integrator"
CERTIFICATE_PROVIDER_APP_NAME = "self-signed-certificates"
INGRESS_REQUIRER_APP_NAME = "flask-k8s"
BIND_APP_NAME = "bind"
GATEWAY_BASE = "ubuntu@24.04"
BIND_BASE = "ubuntu@22.04"
BIND_CHANNEL = "latest/edge"
CERTIFICATE_PROVIDER_CHANNEL = "1/edge"
INGRESS_REQUIRER_CHANNEL = "latest/edge"
TEST_EXTERNAL_HOSTNAME_CONFIG = "gateway.internal"
GATEWAY_CLASS_CONFIG = "ck-gateway"
JUJU_WAIT_TIMEOUT = 10 * 60
K8S_MODEL = "concierge-k8s:testing"
LXD_MODEL = "concierge-lxd:testing"


@pytest.fixture(scope="module", name="juju_k8s")
def juju_k8s_fixture(request: pytest.FixtureRequest):
    """Connect to the Kubernetes model provisioned by Concierge."""
    juju = jubilant.Juju(model=K8S_MODEL)
    juju.wait_timeout = JUJU_WAIT_TIMEOUT
    yield juju

    if request.session.testsfailed:
        logger.error(juju.debug_log(limit=1000))


@pytest.fixture(scope="module", name="juju_lxd")
def juju_lxd_fixture(request: pytest.FixtureRequest):
    """Connect to the LXD model provisioned by Concierge."""
    juju = jubilant.Juju(model=LXD_MODEL)
    juju.wait_timeout = JUJU_WAIT_TIMEOUT
    yield juju

    if request.session.testsfailed:
        logger.error(juju.debug_log(limit=1000))


@pytest.fixture(scope="module", name="charm")
def charm_fixture(charm_paths) -> str:
    """Get the built gateway-api-integrator charm path."""
    return charm_paths[GATEWAY_APP_NAME].path


@pytest.fixture(scope="module", name="application")
def application_fixture(juju_k8s: jubilant.Juju, charm: str) -> str:
    """Deploy gateway-api-integrator to the Kubernetes model."""
    juju_k8s.deploy(charm, app=GATEWAY_APP_NAME, base=GATEWAY_BASE, trust=True)
    juju_k8s.wait(
        lambda status: status.apps[GATEWAY_APP_NAME].app_status.current == "blocked",
        error=jubilant.any_error,
    )
    return GATEWAY_APP_NAME


@pytest.fixture(scope="module", name="certificate_provider_application")
def certificate_provider_application_fixture(juju_k8s: jubilant.Juju) -> str:
    """Deploy self-signed-certificates to the Kubernetes model."""
    juju_k8s.deploy(CERTIFICATE_PROVIDER_APP_NAME, channel=CERTIFICATE_PROVIDER_CHANNEL)
    juju_k8s.wait(
        lambda status: jubilant.all_active(status, CERTIFICATE_PROVIDER_APP_NAME),
        error=jubilant.any_error,
    )
    return CERTIFICATE_PROVIDER_APP_NAME


@pytest.fixture(scope="module", name="ingress_requirer_application")
def ingress_requirer_application_fixture(juju_k8s: jubilant.Juju) -> str:
    """Deploy flask-k8s as the ingress backend."""
    juju_k8s.deploy(INGRESS_REQUIRER_APP_NAME, channel=INGRESS_REQUIRER_CHANNEL)
    return INGRESS_REQUIRER_APP_NAME


@pytest.fixture(scope="module", name="configured_application_with_tls")
def configured_application_with_tls_fixture(
    juju_k8s: jubilant.Juju,
    application: str,
    certificate_provider_application: str,
) -> str:
    """Configure gateway-api-integrator with TLS and an external hostname."""
    juju_k8s.config(
        application,
        {
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        },
    )
    juju_k8s.integrate(application, certificate_provider_application)
    juju_k8s.wait(
        lambda status: jubilant.all_active(status, application, certificate_provider_application),
        error=jubilant.any_error,
    )
    return application


@pytest.fixture(scope="module", name="kube_config")
def kube_config_fixture(request: pytest.FixtureRequest) -> str:
    """Return the Kubernetes configuration file path."""
    kube_config = request.config.getoption("--kube-config")
    assert kube_config, "--kube-config must point to the Kubernetes configuration file"
    return kube_config


@pytest.fixture(scope="module", name="lightkube_client")
def lightkube_client_fixture(kube_config: str, juju_k8s: jubilant.Juju) -> lightkube.Client:
    """Create a lightkube client scoped to the Kubernetes test model."""
    model_name = juju_k8s.show_model().short_name
    config = lightkube.KubeConfig.from_file(kube_config)
    return lightkube.Client(config, namespace=model_name)


@pytest.fixture(scope="module", name="bind_operator")
def bind_operator_fixture(
    juju_lxd: jubilant.Juju,
    juju_k8s: jubilant.Juju,
    configured_application_with_tls: str,
    ingress_requirer_application: str,
) -> str:
    """Deploy Bind on LXD and relate its offer to gateway-api-integrator on Kubernetes."""
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
    juju_k8s.consume(
        f"testing.{BIND_APP_NAME}",
        alias=BIND_APP_NAME,
        controller="concierge-lxd",
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
