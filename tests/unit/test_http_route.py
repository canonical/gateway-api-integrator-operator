# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

# Disable protected access rules to test charm._labels and charm._ingress_provider
# pylint: disable=protected-access
"""Unit tests for http_route resource."""
from unittest.mock import MagicMock

import pytest
from lightkube.core.client import Client
from ops.testing import Harness

from resource_manager.http_route import (
    HTTPRouteRedirectResourceManager,
    HTTPRouteResourceDefinition,
    HTTPRouteResourceManager,
    HTTPRouteType,
)
from state.gateway import GatewayResourceInformation
from state.http_route import (
    HTTPRouteResourceInformation,
    IngressIntegrationDataValidationError,
    IngressIntegrationMissingError,
)


def test_http_route_resource_information_integration_missing(harness: Harness):
    """
    arrange: Given a charm missing ingress integration.
    act: Initialize HTTPRouteResourceInformation state component.
    assert: IngressIntegrationMissingError is raised.
    """
    harness.begin()
    with pytest.raises(IngressIntegrationMissingError):
        HTTPRouteResourceInformation.from_charm(harness.charm, harness.charm._ingress_provider)


def test_http_route_resource_information_validation_error(harness: Harness):
    """
    arrange: Given a charm with ingress integration with invalid data.
    act: Initialize HTTPRouteResourceInformation state component.
    assert: IngressIntegrationDataValidationError is raised.
    """
    harness.add_relation(
        "gateway",
        "test-charm",
    )

    harness.begin()
    with pytest.raises(IngressIntegrationDataValidationError):
        HTTPRouteResourceInformation.from_charm(harness.charm, harness.charm._ingress_provider)


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
    http_route_resource_information = HTTPRouteResourceInformation.from_charm(
        charm, charm._ingress_provider
    )
    gateway_resource_information = GatewayResourceInformation.from_charm(charm)
    http_route_resource_manager = HTTPRouteResourceManager(
        labels=harness.charm._labels,
        client=client_mock,
    )
    redirect_route_resource_manager = HTTPRouteRedirectResourceManager(
        labels=harness.charm._labels,
        client=client_mock,
    )
    redirect_route_resource = redirect_route_resource_manager._gen_resource(
        HTTPRouteResourceDefinition(
            http_route_resource_information,
            gateway_resource_information,
            HTTPRouteType.HTTP,
        )
    )
    https_route_resource = http_route_resource_manager._gen_resource(
        HTTPRouteResourceDefinition(
            http_route_resource_information,
            gateway_resource_information,
            HTTPRouteType.HTTPS,
        )
    )
    assert (
        redirect_route_resource.spec["parentRefs"][0]["sectionName"]
        == f"{harness.model.app.name}-http-listener"
    )
    assert (
        https_route_resource.spec["parentRefs"][0]["sectionName"]
        == f"{harness.model.app.name}-https-listener"
    )
