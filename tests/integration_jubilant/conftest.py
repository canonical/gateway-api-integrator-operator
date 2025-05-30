# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""General configuration module for Jubilant integration tests."""

import pathlib

import jubilant
import pytest


@pytest.fixture(scope="module")
def juju(request: pytest.FixtureRequest):
    """Create a temporary Juju model for testing."""
    keep_models = bool(request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju:  # pylint: disable=redefined-outer-name
        # Disabling pylint warning as this naming is what is suggested.
        juju.wait_timeout = 10 * 60

        yield juju  # run the test

        if request.session.testsfailed:
            log = juju.debug_log(limit=1000)
            print(log, end="")


@pytest.fixture(scope="module")
def app(juju: jubilant.Juju):  # pylint: disable=redefined-outer-name
    # Disabling pylint warning as this naming is what is suggested.
    """Deploy the gateway-api-integrator charm and necessary charms for it."""
    juju.deploy(
        charm_path("gateway-api-integrator"),
        "gateway-api-integrator",
        base="ubuntu@24.04",
        trust=True,
        config={
            "gateway-class": "cilium",
            "external-hostname": "www.gateway.internal",
        },
    )
    juju.deploy("self-signed-certificates")
    juju.integrate(
        "gateway-api-integrator",
        "self-signed-certificates",
    )

    juju.deploy("flask-k8s", channel="latest/edge")
    juju.integrate("gateway-api-integrator:gateway", "flask-k8s")
    juju.wait(jubilant.all_active)

    yield "gateway-api-integrator"  # run the test


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
