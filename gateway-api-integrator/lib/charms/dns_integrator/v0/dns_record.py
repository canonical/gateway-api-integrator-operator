# Copyright 2026 Canonical Ltd.
# Licensed under the Apache2.0. See LICENSE file in charm source for details.

r"""Library to manage the integration with a primary DNS charm.

This library contains the Requires and Provides classes for handling the integration
between an application and a charm providing the `dns_record` integration.
It is completely backwards compatible with the legacy bind.v0.dns_record library.

### Requirer Charm

```python

from charms.dns_integrator.v0 import dns_record

class DNSRecordRequirerCharm(ops.CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.dns_record = dns_record.DNSRecordRequires(self)
        self.framework.observe(self.dns_record.on.relation_joined, self._handler)
        ...

    def _handler(self, events: RelationJoinedEvent) -> None:
        self._update_relations()

    def _update_relations(self) -> None:
        if not self.model.unit.is_leader():
            return
        try:
            self.dns_record.update_relation_data(self._get_dns_record_data())
        except ops.model.ModelError as e:
            logger.error("ERROR while updating relation data: %s", e)
            raise

    def _get_dns_record_data(self) -> list[dns_record.RecordRequest]:
        entries = []
        for request in str(self.config["requests"]).split("\n"):
            try:
                entries.append(self.dns_record.create_record_request(request))
            except dns_record.CreateRecordRequestError:
                logger.error("Invalid entry ignored: '%s'", request)
                continue
        return entries

```

As shown above, the library does not expose any custom event and the user has to rely
on the generic RelationJoined, RelationChanged events to check when DNS data has been changed.

The DNSRecordRequires provides an `update_dns_entries` method to update the relation data by
passing a list of RecordRequest, requesting new DNS records.

### Provider Charm

Following the previous example, this is an example of the provider charm.

```python
from charms.bind.v0.dns_record import DNSRecordProvides

class DNSRecordProviderCharm(ops.CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.dns_record = DNSRecordProvides(self)
        ...

```
The DNSRecordProvides object wraps the list of relations into a `relations` property
and provides an `update_dns_entries` method to update the relation data by passing
a list of RecordRequest. It is expected that the provider updates the status of
those requests before updating the relation data.

```python
class DNSRecordProviderCharm(ops.CharmBase):
    ...

    def _handler(self, _: RelationChangedEvent) -> None:

        for relation in self.dns_record.relations:
            requests = self.dns_record.get_dns_entries(relation)
            for request in requests:
                request.status = Status.APPROVED
            self.dns_record.update_dns_entries(requests, relation)

```

`get_relation_data` and `update_relation_data` are deprecated aliases of
`get_dns_entries` and `update_dns_entries`, kept for backwards compatibility.

Every method taking a `relation` argument accepts `None`, in which case the single
relation on the endpoint is used. A charm integrated with more than one application on
the endpoint must pass the relation explicitly, otherwise `ops.TooManyRelatedAppsError`
is raised. Use the `relations` property to iterate over them.

### Relation data models

Each side of the relation publishes a single application databag, modelled as a whole by
`RequirerData` for the requirer and `ProviderData` for the provider. Those models own the
encoding of the databag fields and all the validation; the `get_*` and `update_*` methods
are thin accessors on top of them. An `update_*` method only touches the field it names
and leaves the rest of the databag alone.

### Automatically allocated domains

A provider may automatically allocate a domain for each of its requirers. It publishes
the allocated domain in its application databag through the optional `ddns-domain` field:

```python
self.dns_record.update_ddns_domain("1403f42c.example.com", relation)
```

and the requirer reads it with:

```python
domain = self.dns_record.get_ddns_domain()
```

By default, the DNS provider should point the automatically allocated domain to the
`ingress-address` of the requirer charm unit. But the `ingress-address` is sometimes a
private address behind DNAT, which can't directly be used as the address of a record.
In that case, a requirer that knows its publicly accessible addresses can optionally
provide them to the provider through the `ddns-addresses` field in its application databag:

```python
self.dns_record.update_ddns_addresses(["10.0.0.1"])
```

and the provider reads them back as a set of `ipaddress.IPv4Address` and
`ipaddress.IPv6Address` with:

```python
addresses = self.dns_record.get_ddns_addresses(relation)
```

Both fields are optional. A charm that knows nothing about them is unaffected.
"""

# The unique Charmhub library identifier, never change it
LIBID = "35f1741937e6405389841e4dc8c29928"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 2

PYDEPS = ["pydantic>=2"]

# pylint: disable=wrong-import-position
import collections
import ipaddress
import itertools
import json
import logging
import re
import typing
import uuid as uuid_module
import warnings
from enum import Enum

import ops
import pydantic

logger = logging.getLogger(__name__)

DEFAULT_RELATION_NAME = "dns-record"
DEFAULT_SECRET_LABEL = "dns-record"  # nosec

DNS_ENTRIES_FIELD = "dns_entries"
DDNS_DOMAIN_FIELD = "ddns-domain"
DDNS_ADDRESSES_FIELD = "ddns-addresses"

DDNS_DOMAIN_MAX_LENGTH = 253
_DDNS_LABEL_PATTERN = re.compile(r"(?!-)[A-Za-z0-9-]{1,63}(?<!-)")


class DnsRecordError(Exception):
    """Base exception for the lib."""

    def __init__(self, msg: str):
        """Initialize a new instance of the exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


class CreateRecordRequestError(DnsRecordError):
    """Exception raised creating the record request fails."""


class Status(str, Enum):
    """Represent the status values.

    Attributes:
        APPROVED: approved
        PERMISSION_DENIED: permission_denied
        CONFLICT: conflict
        INVALID_DATA: invalid_data
        FAILURE: failure
        UNKNOWN: unknown
        PENDING: pending
    """

    APPROVED = "approved"
    PERMISSION_DENIED = "permission_denied"
    CONFLICT = "conflict"
    INVALID_DATA = "invalid_data"
    FAILURE = "failure"
    UNKNOWN = "unknown"
    PENDING = "pending"

    @classmethod
    def _missing_(cls, _: object) -> "Status":
        """Handle the enum when the value is missing.

        Returns:
            value: Status.UNKNOWN.
        """
        return cls(cls.UNKNOWN)


class RecordType(str, Enum):
    """Represent the DNS record types.

    Attributes:
        A: A
        AAAA: AAAA
        CNAME: CNAME
        MX: MX
        DKIM: DKIM
        SPF: SPF
        DMARC: DMARC
        TXT: TXT
        CAA: CAA
        SRV: SRV
        SVCB: SVCB
        HTTPS: HTTPS
        PTR: PTR
        SOA: SOA
        NS: NS
        DS: DS
        DNSKEY: DNSKEY
    """

    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    MX = "MX"
    DKIM = "DKIM"
    SPF = "SPF"
    DMARC = "DMARC"
    TXT = "TXT"
    CAA = "CAA"
    SRV = "SRV"
    SVCB = "SVCB"
    HTTPS = "HTTPS"
    PTR = "PTR"
    SOA = "SOA"
    NS = "NS"
    DS = "DS"
    DNSKEY = "DNSKEY"


class RecordClass(str, Enum):
    """Represent the DNS record classes.

    Attributes:
        IN: IN
    """

    IN = "IN"


class Record(pydantic.BaseModel):
    """DNS record.

    Attributes:
        domain: the domain name.
        host_label: host label.
        ttl: TTL.
        record_class: DNS record class.
        record_type: DNS record type.
        record_data: DNS record value (pydantic.IPvAnyAddress for A/AAAA, str otherwise).
    """

    domain: str = pydantic.Field(min_length=1)
    host_label: str = pydantic.Field(min_length=1)
    ttl: int
    record_class: RecordClass = RecordClass.IN
    record_type: RecordType
    record_data: str | pydantic.IPvAnyAddress

    @pydantic.field_serializer(
        "domain",
        "host_label",
        "ttl",
        "record_class",
        "record_type",
        "record_data",
    )
    def serialize_value(self, value: RecordClass | RecordType | str | int | None) -> str | None:
        """Serialize value.

        Args:
            value: input value

        Returns:
            serialized value
        """
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, int):
            return str(value)
        return str(value.value)

    @pydantic.model_validator(mode="after")
    def validate_model(self) -> "Record":
        """Validate the model.

        Returns:
            A validated Record model

        Raises:
            ValueError: if there is an issue in the model data
        """
        value = self.record_data
        record_type = self.record_type
        if record_type in (RecordType.A, RecordType.AAAA):
            if isinstance(value, pydantic.networks.IPvAnyAddress):
                return self
            if isinstance(value, str):
                try:
                    # mypy is confused by the fact that pydantic interfaces
                    # an external class
                    pydantic.networks.IPvAnyAddress(value)  # type: ignore
                except ValueError as e:
                    raise ValueError(
                        "record_data must be a valid IP address for record_type A or AAAA"
                    ) from e
            else:
                raise ValueError(
                    "record_data must be a string"
                    "or pydantic.IPvAnyAddress for record_type A or AAAA"
                )
        # For other record types, ensure it's a string
        if not isinstance(value, str):
            raise ValueError("record_data must be a string for non-A/AAAA record types")
        return self


class RecordRequest(pydantic.BaseModel):
    """DNS record requested.

    Attributes:
        uuid: UUID for this request.
        status: status for the domain request.
        description: status description for the domain request.
        record: the actual requested DNS record.
    """

    uuid: uuid_module.UUID
    status: Status | None = None
    description: str | None = None
    record: Record | None = None

    @pydantic.model_validator(mode="after")
    def validate_model(self) -> "RecordRequest":
        """Validate the model.

        Returns:
            A validated RecordRequest model

        Raises:
            ValueError: if there is an issue in the model data
        """
        if self.record is None:
            if self.status is None:
                raise ValueError("A record request must have a status if no record is defined")
        return self

    def serialize_as_response(self) -> dict[str, str]:
        """Serialize the RecordRequest as a response.

        Returns:
            The serialized model as a response to a request.
        """
        return self.model_dump(exclude={"record"})

    def serialize_as_request(self) -> dict[str, str]:
        """Serialize the RecordRequest as a request.

        Returns:
            The serialized model as a request.
        """
        request = self.model_dump(exclude={"status", "description", "record"})
        if self.record:
            record = self.record.model_dump()
            request.update(record)
        return request

    @pydantic.field_serializer("uuid")
    def serialize_uuid(self, value: uuid_module.UUID) -> str:
        """Serialize value.

        Args:
            value: input value

        Returns:
            serialized value
        """
        return str(value)


def _decode_dns_entries(value: typing.Any) -> typing.Any:
    """Decode the raw value of the dns_entries databag field.

    The flat entries of the databag are regrouped by uuid and the invalid ones are dropped.

    Args:
        value: the raw value to decode.

    Returns:
        the value to validate as a list of RecordRequest.
    """
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, list) or all(isinstance(entry, RecordRequest) for entry in value):
        return value

    entries: dict[str, dict[str, typing.Any]] = collections.defaultdict(dict)
    for entry in value:
        if not isinstance(entry, dict) or "uuid" not in entry:
            logger.warning("Ignoring a DNS entry without an uuid")
            continue
        entries[entry["uuid"]] |= entry

    requests: list[RecordRequest] = []
    for entry in entries.values():
        try:
            # This works based on the fact that pydantic will ignore extra fields
            entry["record"] = Record.model_validate(entry)
        except pydantic.ValidationError:
            # An entry without a valid record is still a valid status update
            pass
        try:
            requests.append(RecordRequest.model_validate(entry))
        except pydantic.ValidationError:
            logger.warning("Ignoring the invalid DNS entry %s", entry.get("uuid"))
    return requests


def _encode_dns_requests(dns_entries: list[RecordRequest]) -> str:
    """Encode DNS record entries as requests.

    Args:
        dns_entries: the entries to encode.

    Returns:
        the raw value of the dns_entries databag field.
    """
    return json.dumps([entry.serialize_as_request() for entry in dns_entries])


def _encode_dns_responses(dns_entries: list[RecordRequest]) -> str:
    """Encode DNS record entries as responses.

    Args:
        dns_entries: the entries to encode.

    Returns:
        the raw value of the dns_entries databag field.
    """
    return json.dumps([entry.serialize_as_response() for entry in dns_entries])


def _decode_ddns_addresses(value: typing.Any) -> typing.Any:
    """Decode the raw value of the ddns-addresses databag field.

    Args:
        value: the raw value to decode.

    Returns:
        the value to validate as a set of IP addresses.
    """
    if isinstance(value, str):
        return {address.strip() for address in value.split(",") if address.strip()}
    return value


def _encode_ddns_addresses(addresses: set[ipaddress.IPv4Address | ipaddress.IPv6Address]) -> str:
    """Encode the addresses the automatically allocated domain should point at.

    The addresses are sorted so that equal sets are always encoded the same way.

    Args:
        addresses: the addresses to encode.

    Returns:
        the raw value of the ddns-addresses databag field. It is empty when there is no
        address to publish, which removes the field from the databag.
    """
    return ",".join(
        str(address)
        for address in sorted(addresses, key=lambda address: (address.version, address.packed))
    )


def _validate_ddns_domain(domain: str | None) -> str | None:
    """Normalize and validate the automatically allocated domain.

    Args:
        domain: the domain to normalize and validate.

    Returns:
        the normalized domain.

    Raises:
        ValueError: when the domain is not a valid domain name.
    """
    if domain is None:
        return None
    normalized = domain.strip().removesuffix(".")
    if not normalized or len(normalized) > DDNS_DOMAIN_MAX_LENGTH:
        raise ValueError(f"Invalid domain: {domain!r}")
    if not all(_DDNS_LABEL_PATTERN.fullmatch(label) for label in normalized.split(".")):
        raise ValueError(f"Invalid domain: {domain!r}")
    return normalized


def _encode_ddns_domain(domain: str | None) -> str:
    """Encode the automatically allocated domain.

    Args:
        domain: the domain to encode.

    Returns:
        the raw value of the ddns-domain databag field. It is empty when there is no
        domain to publish, which removes the field from the databag.
    """
    return domain or ""


# The DNS record entries, JSON encoded in the databag as requests or as responses.
_DNSRequests = typing.Annotated[
    list[RecordRequest],
    pydantic.BeforeValidator(_decode_dns_entries),
    pydantic.PlainSerializer(_encode_dns_requests),
]
_DNSResponses = typing.Annotated[
    list[RecordRequest],
    pydantic.BeforeValidator(_decode_dns_entries),
    pydantic.PlainSerializer(_encode_dns_responses),
]

# The addresses of the automatically allocated domain, a comma separated list of IP
# addresses in the databag.
_DDNSAddresses = typing.Annotated[
    set[ipaddress.IPv4Address | ipaddress.IPv6Address],
    pydantic.BeforeValidator(_decode_ddns_addresses),
    pydantic.PlainSerializer(_encode_ddns_addresses),
]

# The automatically allocated domain, a plain domain name in the databag.
_DDNSDomain = typing.Annotated[
    str | None,
    pydantic.AfterValidator(_validate_ddns_domain),
    pydantic.PlainSerializer(_encode_ddns_domain),
]


class RequirerData(pydantic.BaseModel):
    """The dns_record application databag published by the requirer.

    The model validates a raw databag and dumps one back, each field with its own wire
    format. Unknown fields are ignored, so that a charm using a newer version of this
    library can't break one using an older version.

    Attributes:
        model_config: the pydantic model configuration.
        dns_entries: the DNS records requested by the requirer.
        ddns_addresses: the addresses the automatically allocated domain should point at.
    """

    model_config = pydantic.ConfigDict(populate_by_name=True, validate_assignment=True)

    dns_entries: _DNSRequests = pydantic.Field(
        default_factory=list,
        validation_alias=DNS_ENTRIES_FIELD,
        serialization_alias=DNS_ENTRIES_FIELD,
    )
    ddns_addresses: _DDNSAddresses = pydantic.Field(
        default_factory=set,
        validation_alias=DDNS_ADDRESSES_FIELD,
        serialization_alias=DDNS_ADDRESSES_FIELD,
    )


class ProviderData(pydantic.BaseModel):
    """The dns_record application databag published by the provider.

    The model validates a raw databag and dumps one back, each field with its own wire
    format. Unknown fields are ignored, so that a charm using a newer version of this
    library can't break one using an older version.

    Attributes:
        model_config: the pydantic model configuration.
        dns_entries: the status of the DNS records requested by the requirer.
        ddns_domain: the domain automatically allocated for the requirer of the relation.
    """

    model_config = pydantic.ConfigDict(populate_by_name=True, validate_assignment=True)

    dns_entries: _DNSResponses = pydantic.Field(
        default_factory=list,
        validation_alias=DNS_ENTRIES_FIELD,
        serialization_alias=DNS_ENTRIES_FIELD,
    )
    ddns_domain: _DDNSDomain = pydantic.Field(
        default=None,
        validation_alias=DDNS_DOMAIN_FIELD,
        serialization_alias=DDNS_DOMAIN_FIELD,
    )


_RelationDataT = typing.TypeVar("_RelationDataT", bound=pydantic.BaseModel)


class DNSRecordBase(ops.Object):
    """Base class for the DNS relation.

    Attributes:
        relations: all the relations on the endpoint handled by this object.
    """

    _remote_data_type: typing.ClassVar[type[RequirerData] | type[ProviderData]]
    _local_data_type: typing.ClassVar[type[RequirerData] | type[ProviderData]]

    def __init__(self, charm: ops.CharmBase, relation_name: str = DEFAULT_RELATION_NAME) -> None:
        """Construct.

        Args:
            charm: the provider charm.
            relation_name: the relation name.
        """
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name

    @property
    def relations(self) -> list[ops.Relation]:
        """Get all the relations on the endpoint handled by this object.

        Returns:
            the list of relations on the endpoint handled by this object.
        """
        return list(self.model.relations[self.relation_name])

    def _get_relation(self, relation: ops.Relation | None = None) -> ops.Relation | None:
        """Resolve the relation to operate on.

        Args:
            relation: the relation to operate on. When None, the single relation on the
                endpoint is used.

        Returns:
            the relation to operate on, or None when there is no relation.
        """
        if relation is not None:
            return relation
        return self.model.get_relation(self.relation_name)

    def _get_remote_data(
        self, model: type[_RelationDataT], relation: ops.Relation | None
    ) -> _RelationDataT | None:
        """Load the remote application databag of a relation into a model.

        Args:
            model: the model to load the databag into.
            relation: the relation to read the data from. When None, the single relation
                on the endpoint is used.

        Returns:
            the remote relation data, or None when there is no relation or the remote
            application published invalid data.
        """
        relation = self._get_relation(relation)
        if relation is None or relation.app is None:
            return None
        try:
            return model.model_validate(dict(relation.data[relation.app]))
        except pydantic.ValidationError as exc:
            logger.warning("Invalid data in relation %s: %s", relation.id, exc)
            return None

    def _update_local_data(self, relation: ops.Relation | None, **fields: typing.Any) -> None:
        """Update fields of the local application databag of a relation.

        Args:
            relation: the relation to update. When None, the single relation on the
                endpoint is used.
            fields: the model fields to set, by name.
        """
        relation = self._get_relation(relation)
        if relation is None:
            return
        databag = relation.data[self.charm.model.app]
        try:
            data = self._local_data_type.model_validate(dict(databag))
        except pydantic.ValidationError as exc:
            logger.warning(
                "Discarding the invalid local data of relation %s: %s", relation.id, exc
            )
            data = self._local_data_type()
        for name, value in fields.items():
            setattr(data, name, value)
        databag.update(data.model_dump(by_alias=True))

    def get_dns_entries(self, relation: ops.Relation | None = None) -> list[RecordRequest] | None:
        """Retrieve the DNS record entries published by the remote application.

        Args:
            relation: the relation to read the entries from. When None, the single
                relation on the endpoint is used.

        Returns:
            the DNS record entries, or None when there is no relation or the remote
            application published invalid data.
        """
        data = self._get_remote_data(self._remote_data_type, relation)
        return data.dns_entries if data is not None else None

    def update_dns_entries(
        self,
        record_requests: list[RecordRequest],
        relation: ops.Relation | None = None,
    ) -> None:
        """Publish DNS record entries in the local application databag.

        Args:
            record_requests: the DNS record entries to publish.
            relation: the relation to update. When None, the single relation on the
                endpoint is used.
        """
        self._update_local_data(relation, dns_entries=record_requests)

    def get_relation_data(
        self, relation: ops.Relation | None = None
    ) -> list[RecordRequest] | None:
        """Retrieve the DNS record entries published by the remote application.

        Deprecated: use `get_dns_entries` instead.

        Args:
            relation: the relation to read the data from. When None, the single relation
                on the endpoint is used.

        Returns:
            the DNS record entries, or None when there is no relation or the remote
            application published invalid data.
        """
        warnings.warn(
            "get_relation_data is deprecated, use get_dns_entries instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.get_dns_entries(relation)

    def update_relation_data(
        self,
        record_requests: list[RecordRequest],
        relation: ops.Relation | None = None,
    ) -> None:
        """Publish DNS record entries in the local application databag.

        Deprecated: use `update_dns_entries` instead.

        Args:
            record_requests: the DNS record entries to publish.
            relation: the relation to update. When None, the single relation on the
                endpoint is used.
        """
        warnings.warn(
            "update_relation_data is deprecated, use update_dns_entries instead",
            DeprecationWarning,
            stacklevel=2,
        )
        self.update_dns_entries(record_requests, relation)


class DNSRecordRequires(DNSRecordBase):
    """Requirer side of the DNS requires relation."""

    _remote_data_type = ProviderData
    _local_data_type = RequirerData

    def __init__(
        self,
        charm: ops.CharmBase,
        relation_name: str = DEFAULT_RELATION_NAME,
        secret_label: str = DEFAULT_SECRET_LABEL,
    ) -> None:
        """Construct.

        Args:
            charm: the provider charm.
            relation_name: the relation name.
            secret_label: the label used for the secret.
        """
        super().__init__(charm, relation_name)
        self.secret_label = secret_label

        try:
            self.model.get_secret(label=secret_label)
        except ops.SecretNotFoundError:
            charm.app.add_secret({"namespace": str(uuid_module.uuid4())}, label=secret_label)

    @staticmethod
    def _create_record_request(
        namespace: uuid_module.UUID,
        data: typing.Iterable[str] | str,
        *,
        status: str = str(Status.UNKNOWN),
        description: str = "",
    ) -> RecordRequest:
        """Create a new RecordRequest.

        Args:
            namespace: uuid namespace for the request
            data: Iterable or string with the information
            status: Optional status
            description: Optional description

        Return:
            A newly created recordRequest

        Raise:
            CreateRecordRequestError: when failing to create the RecordRequest
        """
        try:
            if isinstance(data, str):
                data = tuple(data.split())
            data = list(itertools.islice(data, 6))
            if len(data) < 6:
                raise CreateRecordRequestError(f"Incorrect input: {data}")
            host_label, domain, ttl, record_class, record_type, record_data = data
            return RecordRequest.model_validate(
                {
                    "uuid": uuid_module.uuid5(
                        namespace,
                        " ".join(
                            (host_label, domain, ttl, record_class, record_type, record_data)
                        ),
                    ),
                    "record": Record.model_validate(
                        {
                            "host_label": host_label,
                            "domain": domain,
                            "ttl": int(ttl),
                            "record_class": record_class,
                            "record_type": record_type,
                            "record_data": record_data,
                        }
                    ),
                    "status": status,
                    "description": description,
                }
            )
        except ValueError as e:
            raise CreateRecordRequestError(f"Incorrect input: {data}") from e

    def create_record_request(
        self,
        data: typing.Iterable[str] | str,
        *,
        status: str = str(Status.UNKNOWN),
        description: str = "",
    ) -> RecordRequest:
        """Create a new RecordRequest.

        Args:
            data: Iterable or string with the information
            status: Optional status
            description: Optional description

        Return:
            A newly created recordRequest

        Raise:
            CreateRecordRequestError: when failing to create the RecordRequest
        """
        try:
            secret: ops.Secret = self.model.get_secret(label=self.secret_label)
            secret_content: dict[str, str] = secret.get_content()
        except ops.SecretNotFoundError as e:
            raise CreateRecordRequestError("Namespace not found !") from e
        return self._create_record_request(
            uuid_module.UUID(secret_content["namespace"]),
            data,
            status=status,
            description=description,
        )

    def get_ddns_domain(self, relation: ops.Relation | None = None) -> str | None:
        """Get the domain automatically allocated by the provider, if any.

        Args:
            relation: the relation to read the domain from. When None, the single
                relation on the endpoint is used.

        Returns:
            the automatically allocated domain, or None when the provider didn't
            allocate one or published invalid data.
        """
        data = self._get_remote_data(ProviderData, relation)
        return data.ddns_domain if data is not None else None

    def update_ddns_addresses(
        self,
        addresses: typing.Iterable[str | ipaddress.IPv4Address | ipaddress.IPv6Address] | None,
        relation: ops.Relation | None = None,
    ) -> None:
        """Declare the addresses the automatically allocated domain should point at.

        Args:
            addresses: the addresses to declare. None or an empty iterable removes the
                declaration and lets the provider fall back to `ingress-address`.
            relation: the relation to update. When None, the single relation on the
                endpoint is used.
        """
        self._update_local_data(relation, ddns_addresses=set(addresses or ()))


class DNSRecordProvides(DNSRecordBase):
    """Provider side of the DNS record relation."""

    _remote_data_type = RequirerData
    _local_data_type = ProviderData

    def update_ddns_domain(
        self,
        domain: str | None,
        relation: ops.Relation | None = None,
    ) -> None:
        """Publish the domain automatically allocated for the requirer of a relation.

        Args:
            domain: the allocated domain. None removes any previously published domain.
            relation: the relation to publish the domain to. When None, the single
                relation on the endpoint is used.
        """
        self._update_local_data(relation, ddns_domain=domain)

    def get_ddns_addresses(
        self, relation: ops.Relation | None = None
    ) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        """Get the addresses the requirer declared its allocated domain should point at.

        Args:
            relation: the relation to read the addresses from. When None, the single
                relation on the endpoint is used.

        Returns:
            the declared addresses, or an empty set when the requirer declared none or
            published invalid data.
        """
        data = self._get_remote_data(RequirerData, relation)
        return data.ddns_addresses if data is not None else set()
