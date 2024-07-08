# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

# Disable protected access rules to test charm._labels and charm._ingress_provider
# pylint: disable=protected-access
"""Unit tests for http_route resource."""
from unittest.mock import MagicMock

import pytest
from lightkube.core.client import Client
from ops.testing import Harness

from resource_manager.http_route import HTTPRouteResourceManager
from state.base import State
from state.gateway import GatewayResourceDefinition
from state.http_route import (
    HTTPRouteResourceDefinition,
    HTTPRouteResourceType,
    HTTPRouteType,
    IngressIntegrationDataValidationError,
    IngressIntegrationMissingError,
)


def test_http_route_resource_definition_integration_missing(harness: Harness):
    """
    arrange: Given a charm missing ingress integration.
    act: Initialize HTTPRouteResourceDefinition state component.
    assert: IngressIntegrationMissingError is raised.
    """
    harness.begin()
    with pytest.raises(IngressIntegrationMissingError):
        HTTPRouteResourceDefinition.from_charm(harness.charm, harness.charm._ingress_provider)


def test_http_route_resource_definition_validation_error(harness: Harness):
    """
    arrange: Given a charm with ingress integration with invalid data.
    act: Initialize HTTPRouteResourceDefinition state component.
    assert: IngressIntegrationDataValidationError is raised.
    """
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
    config: dict[str, str],
):
    """
    arrange: Given a charm with valid config and mocked client.
    act: Call _gen_resource from the required state components.
    assert: The k8s resource is correctly generated.
    """
    client_mock = MagicMock(spec=Client)
    harness.update_config(config)
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
        State(
            http_route_resource_definition,
            gateway_resource_definition,
            HTTPRouteResourceType(http_route_type=HTTPRouteType.HTTP),
        )
    )
    https_route_resource = http_route_resource_manager._gen_resource(
        State(
            http_route_resource_definition,
            gateway_resource_definition,
            HTTPRouteResourceType(http_route_type=HTTPRouteType.HTTPS),
        )
    )
    assert (
        http_route_resource.spec["parentRefs"][0]["sectionName"]
        == f"{harness.model.app.name}-http-listener"
    )
    assert (
        https_route_resource.spec["parentRefs"][0]["sectionName"]
        == f"{harness.model.app.name}-https-listener"
    )
