# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""General configuration module for integration tests."""

import logging
import os.path
from typing import AsyncGenerator

import lightkube
import lightkube.config
import lightkube.config.kubeconfig
import lightkube.core
import pytest
import pytest_asyncio
from juju.application import Application
from juju.model import Model
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

TEST_EXTERNAL_HOSTNAME_CONFIG = "gateway.internal"
GATEWAY_CLASS_CONFIG = "cilium"


@pytest_asyncio.fixture(scope="module", name="model")
async def model_fixture(ops_test: OpsTest) -> Model:
    """The current test model."""
    assert ops_test.model
    return ops_test.model


@pytest_asyncio.fixture(scope="module", name="charm")
async def charm_fixture(pytestconfig: pytest.Config) -> str:
    """Get value from parameter charm-file."""
    charm = pytestconfig.getoption("--charm-file")
    assert charm, "--charm-file must be set"
    if not os.path.exists(charm):
        logger.info("Using parent directory for charm file")
        charm = os.path.join("..", charm)
    return charm


@pytest_asyncio.fixture(scope="module", name="application")
async def application_fixture(charm: str, model: Model) -> AsyncGenerator[Application, None]:
    """Deploy the charm."""
    # Deploy the charm and wait for active/idle status
    application = await model.deploy(f"./{charm}", trust=True)
    await model.wait_for_idle(
        apps=[application.name],
        status="blocked",
        raise_on_error=True,
    )
    yield application


@pytest.fixture(scope="module", name="certificate_provider_application_name")
def certificate_provider_application_name_fixture() -> str:
    """Return the name of the certificate provider application deployed for tests."""
    return "self-signed-certificates"


@pytest_asyncio.fixture(scope="module", name="certificate_provider_application")
async def certificate_provider_application_fixture(
    certificate_provider_application_name: str,
    model: Model,
) -> Application:
    """Deploy self-signed-certificates."""
    application = await model.deploy(certificate_provider_application_name, channel="edge")
    await model.wait_for_idle(apps=[certificate_provider_application_name], status="active")
    return application


@pytest.fixture(scope="module", name="ingress_requirer_application_name")
def ingress_requirer_application_name_fixture() -> str:
    """Return the name of the certificate provider application deployed for tests."""
    return "jenkins-k8s"


@pytest_asyncio.fixture(scope="module", name="ingress_requirer_application")
async def ingress_requirer_application_fixture(
    ingress_requirer_application_name: str,
    model: Model,
) -> Application:
    """Deploy jenkins-k8s."""
    application = await model.deploy(
        ingress_requirer_application_name, channel="latest/edge", constraints="mem=1024M"
    )
    await model.wait_for_idle(apps=[ingress_requirer_application_name], status="active")
    return application


@pytest.fixture(scope="module", name="kube_config")
def kube_config_fixture(request: pytest.FixtureRequest) -> str:
    """The kubernetes config file path."""
    kube_config = request.config.getoption("--kube-config")
    assert (
        kube_config
    ), "--kube-confg argument is required which should contain the path to kube config."
    return kube_config


@pytest_asyncio.fixture(scope="module", name="lightkube_client")
async def lightkube_client_fixture(kube_config: str, model: Model) -> lightkube.Client:
    """Deploy self-signed-certificates."""
    config = lightkube.KubeConfig.from_file(kube_config)
    client = lightkube.Client(config, namespace=model.name)
    return client
