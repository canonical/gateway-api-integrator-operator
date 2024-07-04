# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for http_route resource."""
from unittest.mock import MagicMock

import pytest
from lightkube.core.client import Client
from ops.testing import Harness

from resource_manager.http_route import HTTPRouteResourceManager, HTTPRouteType
from state.gateway import GatewayResourceDefinition
from state.http_route import (
    HTTPRouteResourceDefinition,
    IngressIntegrationDataValidationError,
    IngressIntegrationMissingError,
)

from .conftest import GATEWAY_CLASS_CONFIG, TEST_EXTERNAL_HOSTNAME_CONFIG


def test_http_route_resource_definition_integration_missing(harness: Harness):
    harness.begin()
    with pytest.raises(IngressIntegrationMissingError):
        HTTPRouteResourceDefinition.from_charm(harness.charm, harness.charm._ingress_provider)


def test_http_route_resource_definition_validation_error(harness: Harness):
    harness.add_relation(
        "gateway",
        "test-charm",
    )

    harness.begin()
    with pytest.raises(IngressIntegrationDataValidationError):
        HTTPRouteResourceDefinition.from_charm(harness.charm, harness.charm._ingress_provider)


def test_httproute_gen_resource(
    harness: Harness,
    gateway_relation_application_data: dict[str, str],
    gateway_relation_unit_data: dict[str, str],
):
    client_mock = MagicMock(spec=Client)
    harness.update_config(
        {
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        }
    )
    harness.add_relation(
        "gateway",
        "test-charm",
        app_data=gateway_relation_application_data,
        unit_data=gateway_relation_unit_data,
    )

    harness.begin()
    charm = harness.charm
    http_route_resource_definition = HTTPRouteResourceDefinition.from_charm(
        charm, charm._ingress_provider
    )
    gateway_resource_definition = GatewayResourceDefinition.from_charm(charm)
    http_route_resource_manager = HTTPRouteResourceManager(
        labels=harness.charm._labels,
        client=client_mock,
    )
    http_route_resource = http_route_resource_manager._gen_resource(
        http_route_resource_definition, gateway_resource_definition, HTTPRouteType.HTTP
    )
    https_route_resource = http_route_resource_manager._gen_resource(
        http_route_resource_definition, gateway_resource_definition, HTTPRouteType.HTTP
    )

    import logging

    logger = logging.getLogger()

    logger.info("http_route: %r", http_route_resource)
