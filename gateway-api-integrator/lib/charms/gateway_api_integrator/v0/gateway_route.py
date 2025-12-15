# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for the gateway-route relation.

This library contains the Requires and Provides classes for handling the gateway-route
interface.

The `GatewayRouteRequirer` class is used by the Configurator charm to send route
configuration to the Integrator.

The `GatewayRouteProvides` class is used by the Integrator charm to receive route
configuration.
"""

import json
import logging
import typing
from dataclasses import dataclass
from functools import partial
from typing import Any, Dict, List, MutableMapping, Optional, Sequence, Tuple, cast

import pydantic
from ops import EventBase
from ops.charm import CharmBase, RelationEvent
from ops.framework import EventSource, Object, ObjectEvents
from ops.model import ModelError, Relation
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, ValidationError, field_validator

# The unique Charmhub library identifier, never change it
LIBID = "e9aa842e-9df3-4ae9-affc-2ed3dcf12788"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 1

logger = logging.getLogger(__name__)

DEFAULT_RELATION_NAME = "gateway-route"
RELATION_INTERFACE = "gateway-route"


input_validator = partial(field_validator, mode="before")  # type: ignore


class _DatabagModel(BaseModel):
    """Base databag model.

    Attrs:
        model_config: pydantic model configuration.
    """

    model_config = ConfigDict(
        # tolerate additional keys in databag
        extra="ignore",
        # Allow instantiating this class by field name (instead of forcing alias).
        populate_by_name=True,
        # Custom config key: whether to nest the whole datastructure (as json)
        # under a field or spread it out at the toplevel.
        _NEST_UNDER=None,
    )  # type: ignore
    """Pydantic config."""

    @classmethod
    def load(cls, databag: MutableMapping) -> "_DatabagModel":
        """Load this model from a Juju json databag.

        Args:
            databag: Databag content.

        Raises:
            DataValidationError: When model validation failed.

        Returns:
            _DatabagModel: The validated model.
        """
        nest_under = cls.model_config.get("_NEST_UNDER")
        if nest_under:
            return cls.model_validate(json.loads(databag[nest_under]))

        try:
            data = {
                k: json.loads(v)
                for k, v in databag.items()
                # Don't attempt to parse model-external values
                if k in {(f.alias or n) for n, f in cls.model_fields.items()}
            }
        except json.JSONDecodeError as e:
            msg = f"invalid databag contents: expecting json. {databag}"
            logger.error(msg)
            raise DataValidationError(msg) from e

        try:
            return cls.model_validate_json(json.dumps(data))
        except ValidationError as e:
            msg = f"failed to validate databag: {databag}"
            logger.debug(msg, exc_info=True)
            raise DataValidationError(msg) from e

    def dump(
        self, databag: Optional[MutableMapping] = None, clear: bool = True
    ) -> Optional[MutableMapping]:
        """Write the contents of this model to Juju databag.

        Args:
            databag: The databag to write to.
            clear: Whether to clear the databag before writing.

        Returns:
            MutableMapping: The databag.
        """
        if clear and databag:
            databag.clear()

        if databag is None:
            databag = {}
        nest_under = self.model_config.get("_NEST_UNDER")
        if nest_under:
            databag[nest_under] = self.model_dump_json(
                by_alias=True,
                # skip keys whose values are default
                exclude_defaults=True,
            )
            return databag

        dct = self.model_dump(mode="json", by_alias=True, exclude_defaults=True)
        databag.update({k: json.dumps(v) for k, v in dct.items()})
        return databag


class GatewayRouteRequirerAppData(_DatabagModel):
    """Gateway-route requirer application databag model."""

    hostname: str = Field(description="The hostname to serve the application on.")
    paths: List[str] = Field(description="List of paths to serve.")
    model: str = Field(description="The model the application is in.")
    name: str = Field(description="the name of the app requesting gateway-route.")
    port: int = Field(description="The port the app wishes to be exposed.")

    # fields on top of vanilla 'gateway-route' interface:
    strip_prefix: Optional[bool] = Field(
        default=False,
        description="Whether to strip the prefix from the gateway-route url.",
        alias="strip-prefix",
    )
    redirect_https: Optional[bool] = Field(
        default=False,
        description="Whether to redirect http traffic to https.",
        alias="redirect-https",
    )

    scheme: Optional[str] = Field(
        default="http", description="What scheme to use in the generated gateway-route url"
    )

    # pydantic wants 'cls' as first arg
    @input_validator("scheme")
    def validate_scheme(cls, scheme: str) -> str:  # noqa: N805
        """Validate scheme arg."""
        if scheme not in {"http", "https"}:
            raise ValueError("invalid scheme: should be one of `http|https`")
        return scheme

    # pydantic wants 'cls' as first arg
    @input_validator("port")
    def validate_port(cls, port: int) -> int:  # noqa: N805
        """Validate port."""
        assert isinstance(port, int), type(port)
        assert 0 < port < 65535, "port out of TCP range"
        return port


class RequirerSchema(BaseModel):
    """Requirer schema for GatewayRoute."""

    app: GatewayRouteRequirerAppData


@dataclass
class GatewayRouteRequirerData:
    """Data exposed by the gateway-route requirer to the provider."""

    app: "GatewayRouteRequirerAppData"


class GatewayRouteRequirer(Object):
    """Requirer side of the gateway-route relation."""

    def __init__(self, charm: CharmBase, relation_name: str = DEFAULT_RELATION_NAME):
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name
        self._strip_prefix: bool = False
        self._redirect_https: bool = False

    def send_route_configuration(
        self,
        hostname: str,
        paths: List[str],
        port: int,
        name: str,
        model: str,
        scheme: str = "https",
        strip_prefix: bool = False,
        redirect_https: bool = False,
    ):
        """Send route configuration to the integrator.

        Args:
            hostname: The hostname to serve the application on.
            paths: List of paths to serve.
            port: The port of the service.
            name: The application name.
            model: The model name.
        """
        relation = self.charm.model.get_relation(self.relation_name)
        if not relation:
            logger.warning(f"Relation {self.relation_name} not found")
            return

        app_databag = relation.data[self.charm.app]
        try:
            # Ignore pyright errors since pyright does not like aliases.
            GatewayRouteRequirerAppData(  # type: ignore
                hostname=hostname,
                model=model,
                name=name,
                paths=paths,
                scheme=scheme,
                port=port,
                strip_prefix=strip_prefix,
                redirect_https=redirect_https
            ).dump(app_databag)
        except ValidationError as e:
            msg = "failed to validate app data"
            logger.info(msg, exc_info=True)  # log to INFO because this might be expected
            raise DataValidationError(msg) from e


class _GatewayRouteBase(Object):
    """Base class for _GatewayRoute interface classes."""

    def __init__(self, charm: CharmBase, relation_name: str = DEFAULT_RELATION_NAME):
        super().__init__(charm, relation_name)

        self.charm: CharmBase = charm
        self.relation_name = relation_name
        self.app = self.charm.app
        self.unit = self.charm.unit

        observe = self.framework.observe
        rel_events = charm.on[relation_name]
        observe(rel_events.relation_created, self._handle_relation)
        observe(rel_events.relation_joined, self._handle_relation)
        observe(rel_events.relation_changed, self._handle_relation)
        observe(rel_events.relation_departed, self._handle_relation)
        observe(rel_events.relation_broken, self._handle_relation_broken)
        observe(charm.on.leader_elected, self._handle_upgrade_or_leader)  # type: ignore
        observe(charm.on.upgrade_charm, self._handle_upgrade_or_leader)  # type: ignore

    @property
    def relations(self) -> List[Relation]:
        """The list of Relation instances associated with this endpoint."""
        return list(self.charm.model.relations[self.relation_name])

    def _handle_relation(self, event: RelationEvent) -> None:
        """Subclasses should implement this method to handle a relation update."""
        pass

    def _handle_relation_broken(self, event: RelationEvent) -> None:
        """Subclasses should implement this method to handle a relation breaking."""
        pass

    def _handle_upgrade_or_leader(self, event: EventBase) -> None:
        """Subclasses should implement this method to handle upgrades or leadership change."""
        pass


class _GatewayRouteEvent(RelationEvent):
    __args__: Tuple[str, ...] = ()
    __optional_kwargs__: Dict[str, Any] = {}

    @classmethod
    def __attrs__(cls):  # type: ignore
        return cls.__args__ + tuple(cls.__optional_kwargs__.keys())

    def __init__(self, handle, relation, *args, **kwargs):  # type: ignore
        super().__init__(handle, relation)

        if not len(self.__args__) == len(args):
            raise TypeError("expected {} args, got {}".format(len(self.__args__), len(args)))

        for attr, obj in zip(self.__args__, args):
            setattr(self, attr, obj)
        for attr, default in self.__optional_kwargs__.items():
            obj = kwargs.get(attr, default)
            setattr(self, attr, obj)

    def snapshot(self) -> Dict[str, Any]:
        dct = super().snapshot()
        for attr in self.__attrs__():
            obj = getattr(self, attr)
            try:
                dct[attr] = obj
            except ValueError as e:
                raise ValueError(
                    "cannot automagically serialize {}: "
                    "override this method and do it "
                    "manually.".format(obj)
                ) from e

        return dct

    def restore(self, snapshot: Any) -> None:
        super().restore(snapshot)
        for attr, obj in snapshot.items():
            setattr(self, attr, obj)


class GatewayRouteAppDataProvidedEvent(_GatewayRouteEvent):
    """Event representing that gateway-route data has been provided for an app."""

    __args__ = ("name", "model", "hosts", "strip_prefix", "redirect_https")

    if typing.TYPE_CHECKING:
        name: Optional[str] = None
        model: Optional[str] = None
        # sequence of hostname, port dicts
        hosts: Sequence[str] = ()
        strip_prefix: bool = False
        redirect_https: bool = False


class GatewayRouteAppDataRemovedEvent(RelationEvent):
    """Event representing that gateway-route data has been removed for an app."""


class GatewayRouteEndpointsUpdatedEvent(RelationEvent):
    """Event representing that the proxied endpoints have been updated."""


class GatewayRouteProviderEvents(ObjectEvents):
    """Container for IPA Provider events."""

    data_provided = EventSource(GatewayRouteAppDataProvidedEvent)
    data_removed = EventSource(GatewayRouteAppDataRemovedEvent)
    endpoints_updated = EventSource(GatewayRouteEndpointsUpdatedEvent)


class IngressError(RuntimeError):
    """Base class for custom errors raised by this library."""


class NotReadyError(IngressError):
    """Raised when a relation is not ready."""


class DataValidationError(IngressError):
    """Raised when data validation fails on IPU relation data."""


class IngressUrl(BaseModel):
    """Ingress url schema."""

    url: AnyHttpUrl


class GatewayRouteProviderAppData(_DatabagModel):
    """Ingress application databag schema."""

    ingress: Optional[IngressUrl] = None


class GatewayRouteProvider(_GatewayRouteBase):
    """Implementation of the provider of gateway-route."""

    on = GatewayRouteProviderEvents()  # type: ignore

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str = DEFAULT_RELATION_NAME,
    ):
        """Constructor for GatewayRouteProvider.

        Args:
            charm: The charm that is instantiating the instance.
            relation_name: The name of the relation endpoint to bind to
                (defaults to "gateway-route").
        """
        super().__init__(charm, relation_name)

    def _handle_relation(self, event: RelationEvent) -> None:
        # created, joined or changed: if remote side has sent the required data:
        # notify listeners.
        if self.is_ready(event.relation):
            data = self.get_data(event.relation)
            self.on.data_provided.emit(  # type: ignore
                event.relation,
                data.app.name,
                data.app.model,
                data.app.hostname,
                data.app.strip_prefix or False,
                data.app.redirect_https or False,
            )

    def _handle_relation_broken(self, event: RelationEvent) -> None:
        self.on.data_removed.emit(event.relation, event.relation.app)  # type: ignore

    def wipe_gateway_route_data(self, relation: Relation) -> None:
        """Clear gateway-route data from relation."""
        assert self.unit.is_leader(), "only leaders can do this"
        try:
            relation.data
        except ModelError as e:
            logger.warning(
                "error {} accessing relation data for {!r}. "
                "Probably a ghost of a dead relation is still "
                "lingering around.".format(e, relation.name)
            )
            return
        del relation.data[self.app]["gateway-route"]
        self.on.endpoints_updated.emit(relation=relation, app=relation.app)

    @staticmethod
    def _get_requirer_app_data(relation: Relation) -> "GatewayRouteRequirerAppData":
        """Fetch and validate the requirer's app databag."""
        app = relation.app
        if app is None:
            raise NotReadyError(relation)

        databag = relation.data[app]
        return cast(GatewayRouteRequirerAppData, GatewayRouteRequirerAppData.load(databag))

    def get_data(self, relation: Relation) -> GatewayRouteRequirerData:
        """Fetch the remote (requirer) app and units' databags."""
        try:
            return GatewayRouteRequirerData(self._get_requirer_app_data(relation))
        except (pydantic.ValidationError, DataValidationError) as e:
            raise DataValidationError(
                "failed to validate gateway-route requirer data: %s" % str(e)
            ) from e

    def is_ready(self, relation: Optional[Relation] = None) -> bool:
        """The Provider is ready if the requirer has sent valid data."""
        if not relation:
            return any(map(self.is_ready, self.relations))

        try:
            self.get_data(relation)
        except (DataValidationError, NotReadyError) as e:
            logger.info("Provider not ready; validation error encountered: %s" % str(e))
            return False
        return True

    def publish_url(self, relation: Relation, url: str) -> None:
        """Publish to the app databag the ingress url."""
        ingress_url = {"url": url}
        try:
            GatewayRouteProviderAppData(ingress=ingress_url).dump(relation.data[self.app])  # type: ignore
            self.on.endpoints_updated.emit(relation=relation, app=relation.app)
        except pydantic.ValidationError as e:
            # If we cannot validate the url as valid, publish an empty databag and log the error.
            logger.error(f"Failed to validate ingress url '{url}' - got ValidationError {e}")
            logger.error(
                (
                    f"url was not published to ingress relation for {relation.app}."
                    f"This error is likely due to an error or misconfiguration of the"
                    "charm calling this library."
                )
            )
            GatewayRouteProviderAppData(ingress=None).dump(relation.data[self.app])  # type: ignore
