# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests for integration test fixtures."""

from inspect import unwrap
from unittest.mock import MagicMock

from tests.integration import conftest


def test_ingress_requirer_deploys_for_current_architecture(monkeypatch):
    """Deploy the ingress requirer using the architecture under test."""
    juju = MagicMock()
    monkeypatch.setattr(conftest, "current_arch", lambda: "arm64")

    unwrap(conftest.ingress_requirer_application_fixture)(juju)

    assert juju.deploy.call_args.kwargs["constraints"] == {"arch": "arm64"}


def test_certificate_provider_deploys_for_current_architecture(monkeypatch):
    """Deploy the certificate provider using the architecture under test."""
    juju = MagicMock()
    monkeypatch.setattr(conftest, "current_arch", lambda: "arm64")

    unwrap(conftest.certificate_provider_application_fixture)(juju)

    assert juju.deploy.call_args.kwargs["base"] == conftest.GATEWAY_BASE
    assert juju.deploy.call_args.kwargs["constraints"] == {"arch": "arm64"}
