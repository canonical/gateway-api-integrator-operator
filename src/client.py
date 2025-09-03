#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator lightkube client helper."""

import logging
from functools import cache
from typing import cast

from lightkube import Client, KubeConfig
from lightkube.core.client import LabelSelector
from lightkube.core.exceptions import ConfigError
from lightkube.generic_resource import GenericNamespacedResource, create_namespaced_resource
from lightkube.resources.core_v1 import Service

logger = logging.getLogger(__name__)

CUSTOM_RESOURCE_GROUP_NAME = "gateway.networking.k8s.io"
HTTP_ROUTE_RESOURCE_NAME = "HTTPRoute"
HTTP_ROUTE_PLURAL = "httproutes"
GATEWAY_API_MANAGED_TRANSIENT_RESOURCES: list[type[GenericNamespacedResource] | type[Service]] = [
    Service,
    create_namespaced_resource(
        CUSTOM_RESOURCE_GROUP_NAME, "v1", HTTP_ROUTE_RESOURCE_NAME, HTTP_ROUTE_PLURAL
    ),
]
CREATED_BY_LABEL = "gateway-api-integrator.charm.juju.is/managed-by"


class LightKubeInitializationError(Exception):
    """Exception raised when initialization of the lightkube client failed."""


@cache
def get_client(field_manager: str, namespace: str) -> Client:
    """Initialize the lightkube client with the correct namespace and field_manager.

    Args:
        field_manager: field manager for server side apply when patching resources.
        namespace: The k8s namespace in which resources are managed.

    Raises:
        LightKubeInitializationError: When initialization of the lightkube client fails

    Returns:
        Client: The initialized lightkube client
    """
    try:
        # Set field_manager for server-side apply when patching resources
        # Keep this consistent across client initializations
        kubeconfig = KubeConfig.from_service_account()
        client = Client(config=kubeconfig, field_manager=field_manager, namespace=namespace)
    except ConfigError as exc:
        logger.exception("Error initializing the lightkube client.")
        raise LightKubeInitializationError("Error initializing the lightkube client.") from exc

    return client


def application_label_selector(name: str) -> LabelSelector:
    """_summary_.

    Args:
        name: Application name.

    Returns:
        LabelSelector: The generated k8s label selector.
    """
    return cast(LabelSelector, {CREATED_BY_LABEL: name})


def cleanup_all_resources(client: Client, labels: LabelSelector) -> None:
    """_summary_.

    Args:
        client: _description_
        labels: _description_
    """
    for resource_class in GATEWAY_API_MANAGED_TRANSIENT_RESOURCES:
        resources = client.list(res=resource_class, labels=labels)
        for resource in resources:
            if resource.metadata and resource.metadata.name:
                client.delete(res=resource_class, name=resource.metadata.name)
