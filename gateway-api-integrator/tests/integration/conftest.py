# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""General configuration module for integration tests."""

import logging

import jubilant
import lightkube
import pytest

logger = logging.getLogger(__name__)

GATEWAY_APP_NAME = "gateway-api-integrator"
CERTIFICATE_PROVIDER_APP_NAME = "self-signed-certificates"
INGRESS_REQUIRER_APP_NAME = "flask-k8s"
GATEWAY_BASE = "ubuntu@24.04"
CERTIFICATE_PROVIDER_CHANNEL = "1/edge"
INGRESS_REQUIRER_CHANNEL = "latest/edge"
TEST_EXTERNAL_HOSTNAME_CONFIG = "gateway.internal"
GATEWAY_CLASS_CONFIG = "ck-gateway"


@pytest.fixture(scope="module", name="juju")
def juju_model_fixture(request: pytest.FixtureRequest):
    """Create a temporary Juju model for testing."""
    keep_models = bool(request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju_model:
        juju_model.wait_timeout = 10 * 60
        yield juju_model

        if request.session.testsfailed:
            log = juju_model.debug_log(limit=1000)
            logger.debug(log)


@pytest.fixture(scope="module", name="charm")
def charm_fixture(charm_paths) -> str:
    """Get the built gateway-api-integrator charm path."""
    return charm_paths[GATEWAY_APP_NAME].path


@pytest.fixture(scope="module", name="application")
def application_fixture(juju: jubilant.Juju, charm: str) -> str:
    """Deploy the charm and wait for blocked status."""
    juju.deploy(charm, app=GATEWAY_APP_NAME, base=GATEWAY_BASE, trust=True)
    juju.wait(lambda status: status.apps[GATEWAY_APP_NAME].app_status.current == "blocked")
    return GATEWAY_APP_NAME


@pytest.fixture(scope="module", name="certificate_provider_application")
def certificate_provider_application_fixture(juju: jubilant.Juju) -> str:
    """Deploy self-signed-certificates."""
    juju.deploy(CERTIFICATE_PROVIDER_APP_NAME, channel=CERTIFICATE_PROVIDER_CHANNEL)
    juju.wait(lambda status: jubilant.all_active(status, CERTIFICATE_PROVIDER_APP_NAME))
    return CERTIFICATE_PROVIDER_APP_NAME


@pytest.fixture(scope="module", name="ingress_requirer_application")
def ingress_requirer_application_fixture(juju: jubilant.Juju) -> str:
    """Deploy flask-k8s."""
    juju.deploy(INGRESS_REQUIRER_APP_NAME, channel=INGRESS_REQUIRER_CHANNEL)
    return INGRESS_REQUIRER_APP_NAME


@pytest.fixture(scope="module", name="kube_config")
def kube_config_fixture(request: pytest.FixtureRequest) -> str:
    """The kubernetes config file path."""
    kube_config = request.config.getoption("--kube-config")
    assert kube_config, (
        "--kube-config argument is required which should contain the path to kube config."
    )
    return kube_config


@pytest.fixture(scope="module", name="lightkube_client")
def lightkube_client_fixture(kube_config: str, juju: jubilant.Juju) -> lightkube.Client:
    """Create a lightkube client scoped to the test model namespace."""
    model_name = juju.show_model().short_name
    config = lightkube.KubeConfig.from_file(kube_config)
    return lightkube.Client(config, namespace=model_name)


@pytest.fixture(scope="module", name="configured_application_with_tls")
def configured_application_with_tls_fixture(
    juju: jubilant.Juju,
    application: str,
    certificate_provider_application: str,
) -> str:
    """The gateway-api-integrator charm configured and integrated with tls provider."""
    juju.config(
        application,
        {
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        },
    )
    juju.integrate(application, certificate_provider_application)
    juju.wait(
        lambda status: jubilant.all_active(status, application, certificate_provider_application),
        timeout=600,
    )
    return application
