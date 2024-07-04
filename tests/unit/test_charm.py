# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""

from unittest.mock import MagicMock, PropertyMock

import ops
import pytest
import typing
from httpx import Response
from lightkube.core.client import Client
from lightkube.core.exceptions import ApiError, ConfigError
from lightkube.generic_resource import GenericGlobalResource
from lightkube.models.meta_v1 import Status
from ops.model import Secret
from ops.testing import Harness

from charm import LightKubeInitializationError
from resource_manager.secret import CreateSecretError
from resource_manager.http_route import CreateHTTPRouteError
from resource_manager.decorator import InsufficientPermissionError
from .conftest import GATEWAY_CLASS_CONFIG, TEST_EXTERNAL_HOSTNAME_CONFIG


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


def test_deploy_lightkube_error(
    harness: Harness, certificates_relation_data: dict, monkeypatch: pytest.MonkeyPatch
):
    """
    arrange: given a gateway-api-integrator charm with valid tls relation
    and mocked lightkube client.
    act: Change the charm's config to trigger reconciliation.
    assert: the charm goes into error state.
    """
    harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    harness.begin()
    lightkube_get_sa_mock = MagicMock()
    lightkube_get_sa_mock.from_service_account = MagicMock(side_effect=ConfigError)
    monkeypatch.setattr("charm.KubeConfig", lightkube_get_sa_mock)

    with pytest.raises(LightKubeInitializationError):
        harness.update_config(
            {
                "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
                "gateway-class": GATEWAY_CLASS_CONFIG,
            }
        )


@pytest.mark.usefixtures("patch_lightkube_client")
def test_deploy_with_initial_hooks(harness: Harness):
    """
    arrange: given a gateway-api-integrator charm with valid tls relation
    and mocked lightkube client.
    act: Change the charm's config to trigger reconciliation.
    assert: the charm goes into error state.
    """
    harness.begin_with_initial_hooks()


@pytest.mark.parametrize(
    "k8s_api_error_code",
    [
        pytest.param(200, id="no error."),
        pytest.param(403, id="k8s permission error."),
        pytest.param(400, id="bad request."),
    ],
)
@pytest.mark.parametrize(
    "create_secret_error",
    [
        pytest.param(None, id="no error."),
        pytest.param(
            CreateSecretError,
            id="create secret error.",
        ),
    ],
)
def test_reconcile(
    harness: Harness,
    mock_lightkube_client: Client,
    gateway_class_resource: GenericGlobalResource,
    certificates_relation_data: dict[str, str],
    private_key_and_password: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
    create_secret_error: typing.Optional[type[CreateSecretError]],
    k8s_api_error_code: int,
):
    # lightkube client
    mock_lightkube_client.list = MagicMock(return_value=[gateway_class_resource])
    if k8s_api_error_code != 200:
        monkeypatch.setattr(
            "lightkube.models.meta_v1.Status.from_dict",
            MagicMock(return_value=Status(code=k8s_api_error_code)),
        )
        mock_lightkube_client.create.side_effect = ApiError(response=MagicMock(spec=Response))
    else:
        if create_secret_error:
            monkeypatch.setattr(
                "resource_manager.secret.SecretResourceManager._gen_resource",
                MagicMock(side_effect=CreateSecretError),
            )
    # juju secret
    monkeypatch.setattr("ops.jujuversion.JujuVersion.has_secrets", PropertyMock(return_value=True))
    password, private_key = private_key_and_password
    juju_secret_mock = MagicMock(spec=Secret)
    juju_secret_mock.get_content.return_value = {"key": private_key, "password": password}
    monkeypatch.setattr("ops.model.Model.get_secret", MagicMock(return_value=juju_secret_mock))

    # harness
    relation_id = harness.add_relation("certificates", "self-signed-certificates")
    harness.update_relation_data(relation_id, harness.model.app.name, certificates_relation_data)
    harness.set_leader()
    harness.begin()

    if k8s_api_error_code != 200 and k8s_api_error_code != 403:
        with pytest.raises(ApiError):
            harness.update_config(
                {
                    "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
                    "gateway-class": GATEWAY_CLASS_CONFIG,
                }
            )
    elif k8s_api_error_code == 403 or not create_secret_error:
        harness.update_config(
            {
                "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
                "gateway-class": GATEWAY_CLASS_CONFIG,
            }
        )
        if k8s_api_error_code == 403:
            assert harness.charm.unit.status.name == ops.BlockedStatus.name
    else:
        with pytest.raises(RuntimeError):
            harness.update_config(
                {
                    "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
                    "gateway-class": GATEWAY_CLASS_CONFIG,
                }
            )


@pytest.mark.parametrize(
    "exc",
    [
        pytest.param(
            (
                "resource_manager.http_route.HTTPRouteResourceManager._gen_resource",
                CreateHTTPRouteError,
            ),
            id="create http_route error.",
        ),
        pytest.param(
            (
                "resource_manager.http_route.HTTPRouteResourceManager.define_resource",
                InsufficientPermissionError,
            ),
            id="k8s permission error.",
        ),
    ],
)
def test_create_http_route_error(
    harness: Harness,
    mock_lightkube_client: Client,
    gateway_class_resource: GenericGlobalResource,
    certificates_relation_data: dict[str, str],
    private_key_and_password: tuple[str, str],
    gateway_relation_application_data: dict[str, str],
    gateway_relation_unit_data: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    exc: tuple[str, type[Exception]],
):
    # lightkube client
    mock_lightkube_client.list = MagicMock(return_value=[gateway_class_resource])
    patch_target, side_effect = exc
    monkeypatch.setattr(
        patch_target,
        MagicMock(side_effect=side_effect),
    )
    # juju secret
    monkeypatch.setattr("ops.jujuversion.JujuVersion.has_secrets", PropertyMock(return_value=True))
    password, private_key = private_key_and_password
    juju_secret_mock = MagicMock(spec=Secret)
    juju_secret_mock.get_content.return_value = {"key": private_key, "password": password}
    monkeypatch.setattr("ops.model.Model.get_secret", MagicMock(return_value=juju_secret_mock))

    # harness
    relation_id = harness.add_relation("certificates", "self-signed-certificates")
    harness.update_relation_data(relation_id, harness.model.app.name, certificates_relation_data)
    harness.add_relation(
        "gateway",
        "test-charm",
        app_data=gateway_relation_application_data,
        unit_data=gateway_relation_unit_data,
    )
    harness.set_leader()
    harness.begin()

    if side_effect == CreateHTTPRouteError:
        with pytest.raises(RuntimeError):
            harness.update_config(
                {
                    "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
                    "gateway-class": GATEWAY_CLASS_CONFIG,
                }
            )
    else:
        harness.update_config(
            {
                "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
                "gateway-class": GATEWAY_CLASS_CONFIG,
            }
        )
        assert harness.charm.unit.status.name == ops.BlockedStatus.name
