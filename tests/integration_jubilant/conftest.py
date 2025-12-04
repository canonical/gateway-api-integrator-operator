# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""General configuration module for Jubilant integration tests."""

import logging
import os
import pathlib

import jubilant
import pytest

logger = logging.getLogger(__name__)

from typing import NamedTuple


class App(NamedTuple):
    """Holds deployed application information for app_fixture."""

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

        if request.session.testsfailed:
            log = juju_model.debug_log(limit=1000)
            logger.debug(log)


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
def app(
    juju: jubilant.Juju,
    gateway_class: str,
    external_hostname: str,
    charm: str,
):
    """Deploy the gateway-api-integrator charm and necessary charms for it."""
    juju.deploy(
        (charm if charm else charm_path("gateway-api-integrator")),
        "gateway-api-integrator",
        base="ubuntu@24.04",
        trust=True,
        config={
            "gateway-class": gateway_class,
            # "external-hostname": external_hostname,
        },
    )
    juju.deploy("self-signed-certificates")
    juju.integrate(
        "gateway-api-integrator",
        "self-signed-certificates",
    )

    return App("gateway-api-integrator")


@pytest.fixture(scope="module")
def app(juju: jubilant.Juju, gateway_api_integrator: App):
    """Deploy the gateway-api-integrator charm and necessary charms for it."""
    juju.deploy("flask-k8s", channel="latest/edge")
    juju.integrate(f"{gateway_api_integrator.name}:gateway", "flask-k8s")
    juju.wait(jubilant.all_active)

    yield gateway_api_integrator.name  # run the test


@pytest.fixture(scope="module")
def gateway_route_configurator(
    juju: jubilant.Juju, external_hostname: str, pytestconfig: pytest.Config
):
    """Deploy the gateway-api-integrator charm and necessary charms for it."""
    configured_charm_path = next(
        (f for f in pytestconfig.getoption("--charm-file") if "/gateway-route-configurator" in f), None
    )
    juju.deploy(
        (
            str(configured_charm_path)
            if configured_charm_path
            else charm_path("gateway-route-configurator")
        ),
        "gateway-route-configurator",
        base="ubuntu@24.04",
        trust=True,
        config={"hostname": external_hostname, "paths": "/app1,/app2"},
    )

    return App("gateway-route-configurator")


def charm_path(name: str) -> pathlib.Path:
    """Return full absolute path to given test charm.

    Args:
        name: The name of the charm, e.g. "gateway-api-integrator".

    Returns:
        The absolute path to the charm file.
    """
    # We're in tests/integration/conftest.py, so parent*3 is repo top level.
    charm_dir = pathlib.Path(__file__).parent.parent.parent
    charms = [p.absolute() for p in charm_dir.glob(f"{name}_*.charm")]
    assert charms, f"{name}_*.charm not found"
    assert len(charms) == 1, "more than one .charm file, unsure which to use"
    return charms[0]
