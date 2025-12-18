# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""General configuration module for Jubilant integration tests."""

import logging
import os
from typing import NamedTuple

import jubilant
import pytest

logger = logging.getLogger(__name__)


class App(NamedTuple):
    """Holds deployed application information for app_fixture.

    Attributes:
        name (str): The name of the deployed application.
    """

    name: str


@pytest.fixture(scope="module", name="gateway_class")
def gateway_class_fixture():
    """Fixture to provide the gateway class for the charm."""
    yield "cilium"


@pytest.fixture(scope="module", name="external_hostname")
def external_hostname_fixture():
    """Fixture to provide the external hostname for the charm."""
    yield "www.gateway.internal"


@pytest.fixture(scope="module", name="juju")
def juju_model_fixture(request: pytest.FixtureRequest):
    """Create a temporary Juju model for testing."""
    keep_models = bool(request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju_model:
        juju_model.wait_timeout = 10 * 60

        yield juju_model  # run the test


@pytest.fixture(scope="module", name="charm")
def charm_fixture(pytestconfig: pytest.Config) -> str:
    """Get value from parameter charm-file."""
    charm_files = pytestconfig.getoption("--charm-file")
    if charm_files is None:
        charm_files = []

    charm = next((f for f in charm_files if "gateway-api-integrator" in f), None)

    assert charm, "--charm-file must be set"
    if not os.path.exists(charm):
        logger.info("Using parent directory for charm file")
        charm = os.path.join("..", charm)
    return charm


@pytest.fixture(scope="module")
def gateway_api_integrator(
    juju: jubilant.Juju,
    gateway_class: str,
    charm: str,
):
    """Deploy the gateway-api-integrator charm and necessary charms for it."""
    juju.deploy(
        charm,
        "gateway-api-integrator",
        base="ubuntu@24.04",
        trust=True,
        config={
            "gateway-class": gateway_class,
        },
    )
    juju.deploy("self-signed-certificates")
    juju.integrate(
        "gateway-api-integrator",
        "self-signed-certificates",
    )

    return App("gateway-api-integrator")


@pytest.fixture(scope="module")
def gateway_route_configurator(
    juju: jubilant.Juju, external_hostname: str, pytestconfig: pytest.Config
):
    """Deploy the gateway-api-integrator charm and necessary charms for it."""
    configured_charm_path = next(
        (f for f in pytestconfig.getoption("--charm-file") if "/gateway-route-configurator" in f),
        None,
    )
    juju.deploy(
        str(configured_charm_path),
        "gateway-route-configurator",
        base="ubuntu@24.04",
        trust=True,
        config={"hostname": external_hostname, "paths": "/app1,/app2"},
    )

    return App("gateway-route-configurator")
