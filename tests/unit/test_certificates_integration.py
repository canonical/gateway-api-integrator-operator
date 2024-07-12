# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for certificates integration."""

import pytest
from ops.testing import Harness

import tls_relation


@pytest.mark.usefixtures("patch_lightkube_client")
def test_generate_password(harness: Harness):
    """
    arrange: Given a gateway api integrator charm.
    act: run generate password.
    assert: the password generated has the correct format.
    """
    harness.begin()

    tls_rel = tls_relation.TLSRelationService(harness.charm.certificates)

    password = tls_rel.generate_password()
    assert isinstance(password, str)
    assert len(password) == 12
