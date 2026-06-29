# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the helpers module."""

import pytest

from helpers import truncate_k8s_resource_name


@pytest.mark.parametrize(
    "name",
    [
        pytest.param("my-model-my-app-service", id="short name"),
        pytest.param("a" * 63, id="exactly 63 chars"),
    ],
)
def test_truncate_k8s_resource_name_unchanged(name):
    """
    arrange: a name at or below the 63-character limit
    act: call truncate_k8s_resource_name
    assert: the name is returned unchanged
    """
    assert truncate_k8s_resource_name(name) == name


def test_truncate_k8s_resource_name_long_name_at_most_63_chars():
    """
    arrange: a name longer than 63 characters
    act: call truncate_k8s_resource_name
    assert: the result is at most 63 characters
    """
    name = "k8s-stg-a-very-long-model-name-my-application-gateway-api-integrator-service"
    assert len(truncate_k8s_resource_name(name)) <= 63


def test_truncate_k8s_resource_name_long_name_is_deterministic():
    """
    arrange: a name longer than 63 characters
    act: call truncate_k8s_resource_name twice
    assert: the results are identical
    """
    name = "k8s-stg-a-very-long-model-name-my-application-gateway-api-integrator-service"
    assert truncate_k8s_resource_name(name) == truncate_k8s_resource_name(name)


def test_truncate_k8s_resource_name_different_long_names_differ():
    """
    arrange: two different names that are both longer than 63 characters
    act: call truncate_k8s_resource_name on each
    assert: the results are different
    """
    name1 = "k8s-stg-a-very-long-model-name-my-application-gateway-api-integrator-service"
    name2 = "k8s-stg-a-very-long-model-name-my-application-gateway-api-integrator-service-2`"
    assert truncate_k8s_resource_name(name1) != truncate_k8s_resource_name(name2)


def test_truncate_k8s_resource_name_no_trailing_dash_before_suffix():
    """
    arrange: a name where the truncation point falls on a dash
    act: call truncate_k8s_resource_name
    assert: the result contains no double-dash and is at most 63 characters
    """
    name = "a" * 54 + "-" + "b" * 20
    result = truncate_k8s_resource_name(name)
    assert "--" not in result
    assert len(result) <= 63
