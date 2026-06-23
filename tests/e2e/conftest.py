# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""General configuration module for Jubilant integration tests."""

import json
import logging
import os
from pathlib import Path

import jubilant
import pytest

logger = logging.getLogger(__name__)

GATEWAY_API_INTEGRATOR_APP_NAME = "gateway-api-integrator"
INGRESS_CONFIGURATOR_APP_NAME = "ingress-configurator"
ANY_CHARM_INGRESS_REQUIRER_APP_NAME = "any-charm"
ANY_CHARM_INGRESS_REQUIRER_SRC = "ingress_requirer.py"

@pytest.fixture(scope="module", name="gateway_class")
def gateway_class_fixture(pytestconfig: pytest.Config):
    """Fixture to provide the gateway class for the charm."""
    gateway_class = pytestconfig.getoption("--gateway-class")
    yield gateway_class or "cilium"  # default to cilium if not set


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
        GATEWAY_API_INTEGRATOR_APP_NAME,
        base="ubuntu@24.04",
        trust=True,
        config={
            "gateway-class": gateway_class,
        },
    )
    juju.deploy("self-signed-certificates")
    juju.integrate(
        GATEWAY_API_INTEGRATOR_APP_NAME,
        "self-signed-certificates",
    )

    return GATEWAY_API_INTEGRATOR_APP_NAME


@pytest.fixture(scope="module")
def ingress_configurator(
    juju: jubilant.Juju, external_hostname: str
):
    """Deploy the ingress-configurator charm and necessary charms for it."""
    juju.deploy(
        "ingress-configurator",
        app=INGRESS_CONFIGURATOR_APP_NAME,
        channel="latest/edge",
        base="ubuntu@24.04",
        trust=True,
        config={"hostname": external_hostname, "paths": "/app1,/app2"},
    )

    return INGRESS_CONFIGURATOR_APP_NAME


@pytest.fixture(scope="module")
def gateway_route_backend_application(
    juju: jubilant.Juju,
) -> str:
    """Deploy any-charm as a backend HTTP service with ingress requirer."""
    here = Path(__file__).parent
    ingress_lib_path = here.parent.parent / "gateway-api-integrator/lib/charms/traefik_k8s/v2/ingress.py"

    any_charm_src_overwrite = {
        "any_charm.py": (here / ANY_CHARM_INGRESS_REQUIRER_SRC).read_text(encoding="utf-8"),
        "ingress.py": ingress_lib_path.read_text(encoding="utf-8"),
    }

    juju.deploy(
        "any-charm",
        app=ANY_CHARM_INGRESS_REQUIRER_APP_NAME,
        channel="latest/edge",
        config={
            "src-overwrite": json.dumps(any_charm_src_overwrite),
            "python-packages": "\n".join(["charmlibs-apt", "pydantic<2.0"]),
        },
    )
    return ANY_CHARM_INGRESS_REQUIRER_APP_NAME
