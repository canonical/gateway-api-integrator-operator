# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm config."""

from unittest.mock import MagicMock

import pytest
from lightkube.core.client import Client
from lightkube.generic_resource import GenericGlobalResource
from lightkube.models.meta_v1 import ObjectMeta
from ops.testing import Harness

from state.config import CharmConfig, InvalidCharmConfigError

from .conftest import GATEWAY_CLASS_CONFIG


@pytest.mark.parametrize(
    "available_gateway_classes",
    [
        pytest.param(GATEWAY_CLASS_CONFIG, id="available."),
        pytest.param("not-available", id="not available."),
    ],
)
def test_config(harness: Harness, available_gateway_classes: str):
    harness.update_config(
        {
            "gateway-class": GATEWAY_CLASS_CONFIG,
        }
    )
    client_mock = MagicMock(spec=Client)
    client_mock.list = MagicMock(
        return_value=[GenericGlobalResource(metadata=ObjectMeta(name=available_gateway_classes))]
    )
    harness.begin()
    with pytest.raises(InvalidCharmConfigError):
        _ = CharmConfig.from_charm(harness.charm, client_mock)
