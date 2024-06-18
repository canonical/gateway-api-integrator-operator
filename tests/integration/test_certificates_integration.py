# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

# pylint: disable=redefined-outer-name,unused-argument,duplicate-code

"""Integration test for certificates relation."""

import logging

import pytest
from juju.application import Application

logger = logging.getLogger(__name__)
TEST_EXTERNAL_HOSTNAME_CONFIG = "gateway.internal"


@pytest.mark.abort_on_fail
async def test_certificates_relation(
    application: Application, certificate_provider_application: Application
):
    """Deploy the charm together with related charms.

    Assert on the unit status before any relations/configurations take place.
    """
    # await application.set_config({"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG})
    await application.model.add_relation(application.name, certificate_provider_application.name)
    await application.model.wait_for_idle(
        apps=[application.name, certificate_provider_application.name],
        idle_period=30,
        status="active",
    )
