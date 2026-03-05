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
    HTTPRouteResourceDefinition,
    HTTPRouteResourceManager,
    HTTPRouteType,
)
from state.gateway import GatewayResourceInformation
from state.http_route import (
    HTTPRouteResourceInformation,
    IngressIntegrationDataValidationError,
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
        HTTPRouteResourceInformation.from_ingress(harness.charm._ingress_provider, None)


def test_http_route_gen_resource(
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
    http_route_resource_information = HTTPRouteResourceInformation.from_ingress(
        charm._ingress_provider, None
    )
    gateway_resource_information = GatewayResourceInformation.from_charm(charm)
    http_route_resource_manager = HTTPRouteResourceManager(
        labels=harness.charm._labels,
        client=client_mock,
    )
    https_route_resource = http_route_resource_manager._gen_resource(
        HTTPRouteResourceDefinition(
            http_route_resource_information,
            gateway_resource_information,
            HTTPRouteType.HTTPS,
        )
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


def test_http_route_resource_information():
    """
    arrange: Provide valid values for all HTTPRouteResourceInformation fields.
    act: Instantiate HTTPRouteResourceInformation.
    assert: All fields are correctly set.
    """
    info = HTTPRouteResourceInformation(
        application_name="my-app",
        requirer_model_name="my-model",
        service_name="gateway-api-integrator-my-app-service",
        service_port=8080,
        service_port_name="tcp-8080",
        filters=[],
        paths=["/my-model-my-app"],
        hostname="gateway.internal",
    )
    assert info.application_name == "my-app"
    assert info.requirer_model_name == "my-model"
    assert info.service_name == "gateway-api-integrator-my-app-service"
    assert info.service_port == 8080
    assert info.service_port_name == "tcp-8080"
    assert info.filters == []
    assert info.paths == ["/my-model-my-app"]
    assert info.hostname == "gateway.internal"


def test_http_route_resource_information_hostname_none():
    """
    arrange: Provide None as hostname.
    act: Instantiate HTTPRouteResourceInformation.
    assert: hostname is None.
    """
    info = HTTPRouteResourceInformation(
        application_name="my-app",
        requirer_model_name="my-model",
        service_name="gateway-api-integrator-my-app-service",
        service_port=8080,
        service_port_name="tcp-8080",
        filters=[],
        paths=["/my-model-my-app"],
        hostname=None,
    )
    assert info.hostname is None


def test_http_route_resource_information_with_strip_prefix_filter():
    """
    arrange: Provide a URLRewrite filter (strip_prefix use case).
    act: Instantiate HTTPRouteResourceInformation.
    assert: The filters list contains the expected URLRewrite filter.
    """
    url_rewrite_filter = {
        "type": "URLRewrite",
        "urlRewrite": {
            "path": {
                "type": "ReplacePrefixMatch",
                "replacePrefixMatch": "/",
            }
        },
    }
    info = HTTPRouteResourceInformation(
        application_name="my-app",
        requirer_model_name="my-model",
        service_name="gateway-api-integrator-my-app-service",
        service_port=8080,
        service_port_name="tcp-8080",
        filters=[url_rewrite_filter],
        paths=["/my-model-my-app"],
        hostname="gateway.internal",
    )
    assert len(info.filters) == 1
    assert info.filters[0]["type"] == "URLRewrite"


def test_http_route_resource_information_multiple_paths():
    """
    arrange: Provide multiple paths.
    act: Instantiate HTTPRouteResourceInformation.
    assert: All paths are stored correctly.
    """
    info = HTTPRouteResourceInformation(
        application_name="my-app",
        requirer_model_name="my-model",
        service_name="gateway-api-integrator-my-app-service",
        service_port=8080,
        service_port_name="tcp-8080",
        filters=[],
        paths=["/path-a", "/path-b", "/path-c"],
        hostname="gateway.internal",
    )
    assert info.paths == ["/path-a", "/path-b", "/path-c"]


def test_http_route_resource_information_empty_filters_and_paths():
    """
    arrange: Provide empty filters and paths lists.
    act: Instantiate HTTPRouteResourceInformation.
    assert: Both lists are empty.
    """
    info = HTTPRouteResourceInformation(
        application_name="my-app",
        requirer_model_name="my-model",
        service_name="gateway-api-integrator-my-app-service",
        service_port=8080,
        service_port_name="tcp-8080",
        filters=[],
        paths=[],
        hostname=None,
    )
    assert info.filters == []
    assert info.paths == []
