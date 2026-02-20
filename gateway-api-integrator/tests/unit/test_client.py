# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""

from dataclasses import dataclass
from typing import Optional
from unittest.mock import MagicMock

import pytest
from httpx import Response
from lightkube.core.client import Client
from lightkube.core.exceptions import ApiError, ConfigError
from lightkube.models.meta_v1 import Status
from ops.testing import Harness

from client import LightKubeInitializationError, cleanup_all_resources, get_client


def test_get_client_config_error(monkeypatch: pytest.MonkeyPatch):
    """
    arrange: Given a charm with valid tls/gateway integration and mocked client returning 4xx.
    act: Update the charm with valid config.
    assert: ApiError is raised.
    """
    lightkube_get_sa_mock = MagicMock()
    lightkube_get_sa_mock.from_service_account = MagicMock(side_effect=ConfigError)
    monkeypatch.setattr("client.KubeConfig", lightkube_get_sa_mock)
    with pytest.raises(LightKubeInitializationError):
        _ = get_client("", "")


def test_cleanup_resources():
    """
    arrange: Given a charm with valid tls/gateway integration and mocked client returning 4xx.
    act: Update the charm with valid config.
    assert: ApiError is raised.
    """

    @dataclass
    class MockLightKubeMeta:
        """Mock resource metadata class.

        Attrs:
            name: Mock resource name.
        """

        name: Optional[str]

    @dataclass
    class MockLightKubeResource:
        """Mock lightkube resource class.

        Attrs:
            metadata: Mock resource metadata.
        """

        metadata: Optional[MockLightKubeMeta]

    delete_mock = MagicMock()
    client_mock = MagicMock()
    client_mock.list = MagicMock(
        return_value=[MockLightKubeResource(metadata=MockLightKubeMeta(name="test"))]
    )
    client_mock.delete = delete_mock
    cleanup_all_resources(client_mock, {})
    assert delete_mock.call_count == 2

    delete_mock = MagicMock()
    client_mock.delete = delete_mock
    client_mock.list = MagicMock(
        return_value=[MockLightKubeResource(metadata=MockLightKubeMeta(name=None))]
    )
    cleanup_all_resources(client_mock, {})
    delete_mock.assert_not_called()


def test_client_api_error_4xx(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    arrange: given a charm with mocked lightkube client that returns 404.
    act: when agent reconciliation triggers.
    assert: Exception is re-raised.
    """
    monkeypatch.setattr(
        "lightkube.models.meta_v1.Status.from_dict", MagicMock(return_value=Status(code=404))
    )
    lightkube_client_mock = MagicMock(spec=Client)
    lightkube_client_mock.list = MagicMock(side_effect=ApiError(response=MagicMock(spec=Response)))
    monkeypatch.setattr(
        "charm.get_client",
        MagicMock(return_value=lightkube_client_mock),
    )

    with pytest.raises(ApiError):
        harness.begin()
