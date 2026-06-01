# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-route interface library v1.

This library implements the gateway-route interface.

The requirer publishes hostname information. The provider publishes
gateway resource details (gateway name, model/namespace, HTTPS mode)
so the requirer can reference the correct Gateway resource.

With the v1 interface, the requirer is expected to create and manage
its own HTTP/TCP/UDP route resources referencing the provider's Gateway.

## Getting Started

Fetch the library:

```shell
charmcraft fetch-lib charms.gateway_api_integrator.v1.gateway_route
```

### Requirer usage

In the `charmcraft.yaml` of the charm, add the following:

```yaml
requires:
    gateway-route:
        interface: gateway-route
```

```python
from charms.gateway_api_integrator.v1.gateway_route import (
    GATEWAY_ROUTE_RELATION_NAME,
    GatewayRouteRequirer,
    GatewayRouteProviderAppData,
)

class IngressConfiguratorCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.gateway_route = GatewayRouteRequirer(self)
        self.framework.observe(
            self.on[GATEWAY_ROUTE_RELATION_NAME].relation_changed, self._on_gateway_route_changed
        )
        self.framework.observe(
            self.on[GATEWAY_ROUTE_RELATION_NAME].relation_broken, self._on_gateway_route_changed
        )

    def _on_gateway_route_changed(self, event):
        provider_data = self.gateway_route.get_provider_data()
        if provider_data:
            # Use provider_data.gateway_name, provider_data.model_name, provider_data.https_mode
            ...
```

### Provider usage

In the `charmcraft.yaml` of the charm, add the following:

```yaml
provides:
    gateway-route:
        interface: gateway-route
```

```python
from charms.gateway_api_integrator.v1.gateway_route import (
    GATEWAY_ROUTE_RELATION_NAME,
    GatewayRouteProvider,
    HttpsMode,
    GatewayRouteRequirerAppData,
)

class GatewayAPIIntegratorCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.gateway_route = GatewayRouteProvider(self)
        self.framework.observe(
            self.on[GATEWAY_ROUTE_RELATION_NAME].relation_changed, self._on_gateway_route_changed
        )
        self.framework.observe(
            self.on[GATEWAY_ROUTE_RELATION_NAME].relation_broken, self._on_gateway_route_changed
        )

    def _on_gateway_route_changed(self, event):
        for relation in self.model.relations[GATEWAY_ROUTE_RELATION_NAME]:
            requirer_data = self.gateway_route.get_requirer_data(relation)
            if requirer_data:
                # Use requirer_data.hostname, requirer_data.additional_hostnames
                ...
        # Publish provider data to all relations
        self.gateway_route.publish_provider_data(
            gateway_name=self.app.name,
            model_name=self.model.name,
            https_mode=HttpsMode.ENFORCED,
        )
```
"""

import logging
from enum import StrEnum
from typing import Annotated

from ops import CharmBase
from ops.framework import Object
from ops.model import (
    Relation,
    RelationDataTypeError,
)
from pydantic import BeforeValidator, Field, ValidationError
from pydantic.dataclasses import dataclass
from validators import domain

# The unique Charmhub library identifier, never change it
LIBID = "53fdf90019a7406695064ed1e3d2708f"

# Increment this major API version when introducing breaking changes
LIBAPI = 1

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 0

logger = logging.getLogger(__name__)
GATEWAY_ROUTE_RELATION_NAME = "gateway-route"


class GatewayRouteInvalidRelationDataError(Exception):
    """Raised when relation data validation for gateway-route fails."""


def valid_fqdn(value: str) -> str:
    """Validate if value is a valid FQDN (TLDs alone are not allowed).

    Args:
        value: The value to validate.

    Raises:
        ValueError: When value is not a valid domain.
    """
    if not bool(domain(value)):
        raise ValueError(f"Invalid domain: {value}")
    return value


# --- Data models ---


class HttpsMode(StrEnum):
    """HTTPS mode for the gateway.

    Attrs:
        DISABLED: TLS is not configured; only HTTP listener exists.
        ENABLED: TLS is configured; both HTTP and HTTPS listeners exist.
        ENFORCED: TLS is configured and enforce-https is true; HTTP redirects to HTTPS.
    """

    DISABLED = "disabled"
    ENABLED = "enabled"
    ENFORCED = "enforced"


@dataclass
class GatewayRouteRequirerAppData:
    """Requirer application databag schema.

    The requirer provides hostname information so the provider can
    configure TLS certificates and DNS records.

    Attributes:
        hostname: The hostname for the service.
        additional_hostnames: Additional hostnames for the service.
    """

    hostname: Annotated[str, BeforeValidator(valid_fqdn)] | None = Field(
        description="The hostname for the service.", default=None
    )
    additional_hostnames: list[Annotated[str, BeforeValidator(valid_fqdn)]] = Field(
        description="Additional hostnames for the service.", default_factory=list
    )


@dataclass
class GatewayRouteProviderAppData:
    """Provider application databag schema.

    The provider publishes gateway resource details so the requirer
    can construct HTTPRoute resources referencing the correct Gateway.

    Attributes:
        gateway_name: The name of the Gateway resource managed by the provider.
        model_name: The Juju model (K8s namespace) where the Gateway resource lives.
        https_mode: The HTTPS mode indicating how the provider handles TLS.
    """

    gateway_name: str = Field(description="The name of the Gateway resource.")
    model_name: str = Field(
        description="The Juju model (K8s namespace) where the Gateway resource lives."
    )
    https_mode: HttpsMode = Field(
        description="The HTTPS mode: disabled, enabled, or enforced."
    )


# --- Provider ---


class GatewayRouteProvider(Object):
    """Gateway-route interface provider implementation.

    The provider reads hostname data from requirers and publishes
    gateway resource information back.
    """

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str = GATEWAY_ROUTE_RELATION_NAME,
    ) -> None:
        """Initialize the GatewayRouteProvider.

        Args:
            charm: The charm instance using this library.
            relation_name: The name of the relation endpoint.
        """
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name
        self._valid_relations: list[Relation] = []

    @property
    def relations(self) -> list[Relation]:
        """All relations for this endpoint."""
        return self.charm.model.relations.get(self.relation_name, [])

    def get_requirer_data(self, relation: Relation) -> GatewayRouteRequirerAppData:
        """Fetch and validate requirer application data from a relation.

        Args:
            relation: The relation to read from.

        Returns:
            Validated requirer data.

        Raises:
            GatewayRouteInvalidRelationDataError: When data validation fails.
        """
        try:
            return relation.load(GatewayRouteRequirerAppData, relation.app)
        except ValidationError as exc:
            raise GatewayRouteInvalidRelationDataError(
                f"gateway-route data validation failed for relation {relation.id}"
            ) from exc

    def get_all_requirer_data(self) -> dict[int, GatewayRouteRequirerAppData]:
        """Fetch requirer data from all relations.

        Also stores the valid relations for use by publish_provider_data.

        Returns:
            Dictionary mapping relation ID to validated requirer data.
        """
        results: dict[int, GatewayRouteRequirerAppData] = {}
        self._valid_relations = []
        for relation in self.relations:
            try:
                data = self.get_requirer_data(relation)
                results[relation.id] = data
                self._valid_relations.append(relation)
            except GatewayRouteInvalidRelationDataError:
                logger.error(
                    "Skipping relation %s: invalid data", relation.id
                )
        return results

    def publish_provider_data(
        self,
        gateway_name: str,
        model_name: str,
        https_mode: HttpsMode,
    ) -> None:
        """Publish gateway information to requirers with valid data.

        Only publishes to relations previously validated by get_all_requirer_data.

        Args:
            gateway_name: The name of the Gateway resource.
            model_name: The Juju model (K8s namespace) of the Gateway resource.
            https_mode: The HTTPS mode for the gateway.

        Raises:
            GatewayRouteInvalidRelationDataError: When data validation fails.
        """
        if not self.charm.unit.is_leader():
            return

        for relation in self._valid_relations:
            self._publish_to_relation(relation, gateway_name, model_name, https_mode)

    def _publish_to_relation(
        self,
        relation: Relation,
        gateway_name: str,
        model_name: str,
        https_mode: HttpsMode,
    ) -> None:
        """Publish provider data to a specific relation.

        Args:
            relation: The relation to publish to.
            gateway_name: The name of the Gateway resource.
            model_name: The Juju model (K8s namespace) of the Gateway resource.
            https_mode: The HTTPS mode for the gateway.

        Raises:
            GatewayRouteInvalidRelationDataError: When data fails to save.
        """
        try:
            app_data = GatewayRouteProviderAppData(
                gateway_name=gateway_name,
                model_name=model_name,
                https_mode=https_mode,
            )
            relation.save(app_data, self.charm.app)
        except (ValidationError, RelationDataTypeError) as exc:
            logger.error("Failed to publish provider data to relation %s.", relation.id)
            raise GatewayRouteInvalidRelationDataError(
                "Failed to publish provider relation data."
            ) from exc


# --- Requirer ---


class GatewayRouteRequirer(Object):
    """Gateway-route interface requirer implementation.

    The requirer provides hostname information and reads back
    gateway resource details from the provider.
    """

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str = GATEWAY_ROUTE_RELATION_NAME,
    ) -> None:
        """Initialize the GatewayRouteRequirer.

        Args:
            charm: The charm instance using this library.
            relation_name: The name of the relation endpoint.
        """
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name

    @property
    def relation(self) -> Relation | None:
        """The relation instance for this endpoint."""
        return self.charm.model.get_relation(self.relation_name)

    def publish_requirer_data(
        self,
        hostname: str,
        additional_hostnames: list[str] | None = None,
    ) -> None:
        """Publish hostname data to the provider.

        Args:
            hostname: The hostname for the service.
            additional_hostnames: Additional hostnames for the service.

        Raises:
            GatewayRouteInvalidRelationDataError: When data validation fails.
        """
        relation = self.relation
        if not relation or not self.charm.unit.is_leader():
            return

        try:
            app_data = GatewayRouteRequirerAppData(
                hostname=hostname,
                additional_hostnames=additional_hostnames or [],
            )
            relation.save(app_data, self.charm.app)
        except (ValidationError, RelationDataTypeError) as exc:
            logger.error("Failed to publish requirer data.")
            raise GatewayRouteInvalidRelationDataError(
                "Failed to publish requirer relation data."
            ) from exc

    def get_provider_data(self) -> GatewayRouteProviderAppData | None:
        """Fetch provider application data from the relation.

        Returns:
            Validated provider data or None if not yet available.

        Raises:
            GatewayRouteInvalidRelationDataError: When data validation fails.
        """
        relation = self.relation
        if not relation or not relation.app:
            return None

        try:
            return relation.load(GatewayRouteProviderAppData, relation.app)
        except ValidationError as exc:
            raise GatewayRouteInvalidRelationDataError(
                "gateway-route provider data validation failed."
            ) from exc
