# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Disable protected access rules to test charm._labels and charm._ingress_provider
# Disable duplicate-code as we're initializing the http-route resource the same way as in charm.py
# pylint: disable=protected-access,duplicate-code
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
        HTTPRouteResourceInformation.from_charm(
            harness.charm, harness.charm._ingress_provider, harness.charm._gateway_route_provider
        )


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
        HTTPRouteResourceInformation.from_charm(
            harness.charm, harness.charm._ingress_provider, harness.charm._gateway_route_provider
        )


def test_httproute_gen_resource(
    harness: Harness,
    gateway_relation: dict[str, dict[str, str]],
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
        app_data=gateway_relation["app_data"],
        unit_data=gateway_relation["unit_data"],
    )

    harness.begin()
    charm = harness.charm
    http_route_resource_information = HTTPRouteResourceInformation.from_charm(
        charm, charm._ingress_provider, harness.charm._gateway_route_provider
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
            http_route_resource_information.strip_prefix,
        )
    )
    https_route_resource = http_route_resource_manager._gen_resource(
        HTTPRouteResourceDefinition(
            http_route_resource_information,
            gateway_resource_information,
            HTTPRouteType.HTTPS,
            http_route_resource_information.strip_prefix,
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


def test_patch_http_route(mock_lightkube_client: MagicMock):
    """
    arrange: Given an HTTPRouteResourceManager with mocked lightkube client.
    act: Call _patch_resource.
    assert: The mocked client method is called.
    """
    http_route_resource_manager = HTTPRouteResourceManager(
        labels={},
        client=mock_lightkube_client,
    )
    http_route_resource_manager._patch_resource("", None)
    mock_lightkube_client.patch.assert_called_once()
