# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""

from dataclasses import dataclass
from typing import Optional
from unittest.mock import MagicMock

import pytest
from lightkube.core.exceptions import ConfigError

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
