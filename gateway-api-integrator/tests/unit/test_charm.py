# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""

from unittest.mock import MagicMock

import ops
import pytest
from httpx import Response
from lightkube.core.exceptions import ApiError
from lightkube.models.meta_v1 import Status
from ops.testing import Harness

from resource_manager.permission import InsufficientPermissionError

from .conftest import GATEWAY_CLASS_CONFIG, TEST_EXTERNAL_HOSTNAME_CONFIG


@pytest.mark.usefixtures("client_with_mock_external")
@pytest.mark.usefixtures("patch_lightkube_client")
def test_deploy_invalid_config(harness: Harness, certificates_relation_data: dict):
    """
    arrange: given a stock gateway-api-integrator charm.
    act: Add a relation to tls provider while config is invalid.
    assert: the charm stays in blocked state.
    """
    harness.begin()

    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )

    assert harness.charm.unit.status.name == ops.BlockedStatus.name


@pytest.mark.usefixtures("patch_lightkube_client")
def test_deploy_missing_tls(harness: Harness):
    """
    arrange: given a stock gateway-api-integrator charm.
    act: Change the charm's config while tls is not ready.
    assert: the charm stays in blocked state.
    """
    harness.begin()

    harness.update_config(
        {"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG, "gateway-class": GATEWAY_CLASS_CONFIG}
    )

    assert harness.charm.unit.status.name == ops.BlockedStatus.name


@pytest.mark.parametrize(
    "error_code",
    [
        pytest.param(401, id="unauthorized."),
        pytest.param(400, id="bad request."),
        pytest.param(404, id="not found."),
    ],
)
def test_reconcile_api_error_4xx(
    harness: Harness,
    client_with_mock_external: MagicMock,
    certificates_relation_data: dict[str, str],
    gateway_relation: dict[str, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
    error_code: int,
    config: dict[str, str],
):  # pylint: disable=too-many-arguments, too-many-positional-arguments
    """
    arrange: Given a charm with valid tls/gateway integration and mocked client returning 4xx.
    act: Update the charm with valid config.
    assert: ApiError is raised.
    """
    harness.set_leader()
    monkeypatch.setattr(
        "lightkube.models.meta_v1.Status.from_dict",
        MagicMock(return_value=Status(code=error_code)),
    )
    monkeypatch.setattr(
        "resource_manager.gateway.GatewayResourceManager.current_gateway_resource",
        MagicMock(return_value=None),
    )

    client_with_mock_external.create.side_effect = ApiError(response=MagicMock(spec=Response))
    harness.add_relation(
        "gateway",
        "requirer-charm",
        app_data=gateway_relation["app_data"],
        unit_data=gateway_relation["unit_data"],
    )
    relation_id = harness.add_relation("certificates", "self-signed-certificates")
    harness.update_relation_data(relation_id, harness.model.app.name, certificates_relation_data)
    harness.begin()

    with pytest.raises(ApiError):
        harness.update_config(config)


def test_reconcile_api_error_forbidden(
    harness: Harness,
    client_with_mock_external: MagicMock,
    certificates_relation_data: dict[str, str],
    gateway_relation: dict[str, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
    config: dict[str, str],
):  # pylint: disable=too-many-arguments, too-many-positional-arguments
    """
    arrange: Given a charm with valid tls/gateway integration and mocked client returning 403.
    act: Update the charm with valid config.
    assert: The charm correctly goes into blocked state due to insufficient permission.
    """
    harness.set_leader()
    monkeypatch.setattr(
        "lightkube.models.meta_v1.Status.from_dict",
        MagicMock(return_value=Status(code=403)),
    )
    monkeypatch.setattr(
        "resource_manager.gateway.GatewayResourceManager.current_gateway_resource",
        MagicMock(return_value=None),
    )
    client_with_mock_external.create.side_effect = ApiError(response=MagicMock(spec=Response))
    harness.add_relation(
        "gateway",
        "requirer-charm",
        app_data=gateway_relation["app_data"],
        unit_data=gateway_relation["unit_data"],
    )
    relation_id = harness.add_relation("certificates", "self-signed-certificates")
    harness.update_relation_data(relation_id, harness.model.app.name, certificates_relation_data)
    harness.begin()

    harness.update_config(config)

    assert harness.charm.unit.status.name == ops.BlockedStatus.name
    assert "juju trust" in harness.charm.unit.status.message


@pytest.mark.usefixtures("client_with_mock_external")
def test_create_http_route_insufficient_permission(
    harness: Harness,
    certificates_relation_data: dict[str, str],
    gateway_relation: dict[str, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
    config: dict[str, str],
):  # pylint: disable=too-many-arguments, too-many-positional-arguments
    """
    arrange: Given a charm with valid tls/gateway integration and mocked
    http_route resource manager returning 403 error.
    act: Update the charm with valid config.
    assert: The charm correctly goes into blocked state due to insufficient permission.
    """
    monkeypatch.setattr(
        "resource_manager.http_route.HTTPRouteResourceManager.define_resource",
        MagicMock(side_effect=InsufficientPermissionError),
    )
    monkeypatch.setattr(
        "resource_manager.gateway.GatewayResourceManager.current_gateway_resource",
        MagicMock(return_value=None),
    )

    relation_id = harness.add_relation("certificates", "self-signed-certificates")
    harness.update_relation_data(relation_id, harness.model.app.name, certificates_relation_data)
    harness.add_relation(
        "gateway",
        "ingress-requirer",
        app_data=gateway_relation["app_data"],
        unit_data=gateway_relation["unit_data"],
    )
    harness.set_leader()
    harness.begin()

    harness.update_config(config)

    assert harness.charm.unit.status.name == ops.BlockedStatus.name
