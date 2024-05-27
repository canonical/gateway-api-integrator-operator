#!/usr/bin/env python3

# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import logging

import pytest
from juju.application import Application

logger = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
async def test_deploy(application: Application):
    """Deploy the charm together with related charms.

    Assert on the unit status before any relations/configurations take place.
    """
    unit = application.units[0]
    assert unit.workload_status_message == "Waiting for TLS."
