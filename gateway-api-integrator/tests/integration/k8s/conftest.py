# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Kubernetes model fixture for integration tests."""

import logging

import jubilant
import pytest

from tests.integration.conftest import JUJU_WAIT_TIMEOUT

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", name="juju")
def juju_model_fixture(request: pytest.FixtureRequest):
    """Create a temporary model on the active Kubernetes controller."""
    keep_models = bool(request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju:
        juju.wait_timeout = JUJU_WAIT_TIMEOUT
        yield juju

        if request.session.testsfailed:
            logger.debug(juju.debug_log(limit=1000))
