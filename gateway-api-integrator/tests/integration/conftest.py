# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""General configuration module for integration tests."""

import json
import logging
from pathlib import Path

import jubilant
import lightkube
import pytest
from opcli.core.env import current_arch

logger = logging.getLogger(__name__)

GATEWAY_APP_NAME = "gateway-api-integrator"
CERTIFICATE_PROVIDER_APP_NAME = "self-signed-certificates"
INGRESS_REQUIRER_APP_NAME = "ingress-requirer"
GATEWAY_BASE = "ubuntu@24.04"
CERTIFICATE_PROVIDER_CHANNEL = "1/edge"
INGRESS_REQUIRER_CHANNEL = "latest/beta"
TEST_EXTERNAL_HOSTNAME_CONFIG = "gateway.internal"
GATEWAY_CLASS_CONFIG = "ck-gateway"
JUJU_WAIT_TIMEOUT = 10 * 60


@pytest.fixture(scope="module", name="juju")
def juju_model_fixture(request: pytest.FixtureRequest):
    """Create a temporary Juju model for testing."""
    keep_models = bool(request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju_model:
        juju_model.wait_timeout = JUJU_WAIT_TIMEOUT
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
    juju.deploy(
        charm,
        app=GATEWAY_APP_NAME,
        base=GATEWAY_BASE,
        constraints={"arch": current_arch()},
        trust=True,
    )
    juju.wait(
        lambda status: status.apps[GATEWAY_APP_NAME].app_status.current == "blocked",
        error=jubilant.any_error,
    )
    return GATEWAY_APP_NAME


@pytest.fixture(scope="module", name="certificate_provider_application")
def certificate_provider_application_fixture(juju: jubilant.Juju) -> str:
    """Deploy self-signed-certificates."""
    juju.deploy(
        CERTIFICATE_PROVIDER_APP_NAME,
        channel=CERTIFICATE_PROVIDER_CHANNEL,
        base=GATEWAY_BASE,
        constraints={"arch": current_arch()},
    )
    juju.wait(
        lambda status: jubilant.all_active(status, CERTIFICATE_PROVIDER_APP_NAME),
        error=jubilant.any_error,
    )
    return CERTIFICATE_PROVIDER_APP_NAME


@pytest.fixture(scope="module", name="ingress_requirer_application")
def ingress_requirer_application_fixture(juju: jubilant.Juju) -> str:
    """Deploy any-charm as an ingress requirer with a unit-local HTTP server."""
    tests_dir = Path(__file__).parent
    ingress_lib_path = tests_dir.parent.parent / "lib/charms/traefik_k8s/v2/ingress.py"
    src_overwrite = {
        "any_charm.py": (tests_dir / "ingress_requirer.py").read_text(encoding="utf-8"),
        "ingress.py": ingress_lib_path.read_text(encoding="utf-8"),
    }
    juju.deploy(
        "any-charm",
        app=INGRESS_REQUIRER_APP_NAME,
        channel=INGRESS_REQUIRER_CHANNEL,
        base=GATEWAY_BASE,
        constraints={"arch": current_arch()},
        config={
            "python-packages": "pydantic<2.0",
            "src-overwrite": json.dumps(src_overwrite),
        },
    )
    juju.wait(
        lambda status: jubilant.all_active(status, INGRESS_REQUIRER_APP_NAME),
        error=jubilant.any_error,
    )
    juju.run(f"{INGRESS_REQUIRER_APP_NAME}/0", "rpc", {"method": "start_server"})
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
        error=jubilant.any_error,
    )
    return application


@pytest.fixture(scope="module", name="configured_application_without_tls")
def configured_application_without_tls_fixture(
    juju: jubilant.Juju,
    application: str,
) -> str:
    """The gateway-api-integrator charm configured without a TLS provider."""
    juju.config(
        application,
        {
            "external-hostname": "",
            "enforce-https": False,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        },
    )
    juju.wait(
        lambda status: jubilant.all_active(status, application),
        error=jubilant.any_error,
    )
    return application
