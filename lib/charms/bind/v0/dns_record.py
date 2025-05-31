# Copyright 2024 Canonical Ltd.
# Licensed under the Apache2.0. See LICENSE file in charm source for details.

"""Library to manage the integration with the Bind charm.

This library contains the Requires and Provides classes for handling the integration
between an application and a charm providing the `dns_record` integration.

### Requirer Charm

```python

from charms.bind.v0.dns_record import DNSRecordRequires

class DNSRecordRequirerCharm(ops.CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.dns_record = DNSRecordRequires(self)
        self.framework.observe(self.dns_record.on.dns_record_request_processed, self._handler)
        ...

    def _handler(self, events: DNSRecordRequestProcessed) -> None:
        ...

```

As shown above, the library provides a custom event to handle the scenario in
which new DNS data has been added or updated.

The DNSRecordRequires provides an `update_relation_data` method to update the relation data by
passing a `DNSRecordRequirerData` data object, requesting new DNS records.

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
and provides an `update_relation_data` method to update the relation data by passing
a `DNSRecordRelationData` data object.

```python
class DNSRecordProviderCharm(ops.CharmBase):
    ...

    def _on_config_changed(self, _) -> None:
        for relation in self.model.relations[self.dns_record.relation_name]:
            self.dns_record.update_relation_data(relation, self._get_dns_record_data())

```
"""

# The unique Charmhub library identifier, never change it
LIBID = "908bcd1f0ad14cabbc9dca25fa0fc87c"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 3

PYDEPS = ["pydantic>=2"]

# pylint: disable=wrong-import-position
import json
import logging
from enum import Enum
from typing import Annotated, Dict, List, Optional, Tuple, cast
from uuid import UUID

import ops
from pydantic import (
    BaseModel,
    Field,
    IPvAnyAddress,
    PlainValidator,
    ValidationError,
    ValidationInfo,
)

logger = logging.getLogger(__name__)

DEFAULT_RELATION_NAME = "dns-record"


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


class DNSProviderData(BaseModel):
    """Represent the DNS provider data.

    Attributes:
        uuid: UUID for the domain request.
        status: status for the domain request.
        description: status description for the domain request.
    """

    uuid: UUID
    status: Status
    description: Optional[str] = None


class DNSRecordProviderData(BaseModel):
    """List of entries for the provider to manage.

    Attributes:
        dns_entries: list of entries to manage.
    """

    dns_entries: List[DNSProviderData]

    def to_relation_data(self) -> Dict[str, str]:
        """Convert an instance of DNSRecordProviderData to the relation representation.

        Returns:
            Dict containing the representation.
        """
        dumped_model = self.model_dump(exclude_unset=True)
        dumped_data = {}
        for key, value in dumped_model.items():
            dumped_data[key] = json.dumps(value, default=str)
        return dumped_data

    @classmethod
    def from_relation(cls, relation: ops.Relation) -> "DNSRecordProviderData":
        """Initialize a new instance of the DNSRecordProviderData class from the relation.

        Args:
            relation: the relation.

        Returns:
            A DNSRecordProviderData instance.

        Raises:
            ValueError: if the value is not parseable.
        """
        try:
            loaded_data = {}
            app = cast(ops.Application, relation.app)
            relation_data = relation.data[app]
            for key, value in relation_data.items():
                loaded_data[key] = json.loads(value)
            return DNSRecordProviderData.model_validate(loaded_data)
        except json.JSONDecodeError as ex:
            raise ValueError from ex


class RequirerEntry(BaseModel):
    """DNS requirer entries requested.

    Attributes:
        domain: the domain name.
        host_label: host label.
        ttl: TTL.
        record_class: DNS record class.
        record_type: DNS record type.
        record_data: the record value.
        uuid: UUID for this entry.
    """

    domain: str = Field(min_length=1)
    host_label: str = Field(min_length=1)
    ttl: Optional[int] = None
    record_class: Optional[RecordClass] = None
    record_type: Optional[RecordType] = None
    record_data: IPvAnyAddress
    uuid: UUID

    def validate_dns_entry(self, _: ValidationInfo) -> "RequirerEntry":
        """Validate DNS entries.

        Returns:
            the DNS entry if valid.
        """
        validated_entry = RequirerEntry.model_validate(self)
        # Additional validations will be done here in the form of assertions
        # assert validated_entry.domain == "cloud.canonical.com"
        return validated_entry


class DNSRecordRequirerData(BaseModel):
    """List of domains for the provider to manage.

    Attributes:
        dns_entries: list of entries to manage.
    """

    dns_entries: List[Annotated[RequirerEntry, PlainValidator(RequirerEntry.validate_dns_entry)]]

    def to_relation_data(self) -> Dict[str, str]:
        """Convert an instance of DNSRecordRequirerData to the relation representation.

        Returns:
            Dict containing the representation.
        """
        dumped_model = self.model_dump(exclude_unset=True)
        dumped_data = {
            "dns_entries": json.dumps(dumped_model["dns_entries"], default=str),
        }
        return dumped_data

    @classmethod
    def from_relation(
        cls, relation: ops.Relation
    ) -> Tuple["DNSRecordRequirerData", "DNSRecordProviderData"]:
        """Get a Tuple of DNSRecordRequirerData and DNSRecordProviderData from the relation data.

        Args:
            relation: the relation.

        Returns:
            the relation data and the processed entries for it.

        Raises:
            ValueError: if the value is not parseable.
        """
        try:
            app = cast(ops.Application, relation.app)
            relation_data = relation.data[app]
            dns_entries = (
                json.loads(relation_data["dns_entries"]) if "dns_entries" in relation_data else []
            )
            valid_entries = []
            invalid_entries = []
            for dns_entry in dns_entries:
                try:
                    if "uuid" not in dns_entry:
                        logger.warning("Received DNS entry without an UUID")
                        continue
                    validated_entry = RequirerEntry.model_validate(dns_entry)
                    valid_entries.append(validated_entry)
                except ValidationError as ex:
                    provider_data = DNSProviderData(
                        uuid=dns_entry["uuid"],
                        status=Status.INVALID_DATA,
                        description=str(ex.errors()),
                    )
                    invalid_entries.append(provider_data)
            return (
                DNSRecordRequirerData(
                    dns_entries=valid_entries,
                ),
                DNSRecordProviderData(dns_entries=invalid_entries),
            )

        except json.JSONDecodeError as ex:
            logger.warning("Invalid relation data %s", ex)
            raise ValueError from ex


class DNSRecordRequestProcessed(ops.RelationEvent):
    """DNS event emitted when a new request is processed.

    Attributes:
        dns_entries: list of processed entries.
    """

    def get_dns_record_provider_relation_data(self) -> DNSRecordProviderData:
        """Get a DNSRecordProviderData for the relation data.

        Returns:
            the DNSRecordProviderData for the relation data.
        """
        return DNSRecordProviderData.from_relation(self.relation)

    @property
    def dns_entries(self) -> Optional[List[DNSProviderData]]:
        """Fetch the DNS entries from the relation."""
        return self.get_dns_record_provider_relation_data().dns_entries


class DNSRecordRequestReceived(ops.RelationEvent):
    """DNS event emitted when a new request is made.

    Attributes:
        dns_record_requirer_relation_data: the DNS requirer relation data.
        dns_entries: list of requested entries.
        processed_entries: list of processed entries from the original request.
    """

    @property
    def dns_record_requirer_relation_data(
        self,
    ) -> Tuple[DNSRecordRequirerData, DNSRecordProviderData]:
        """Get the requirer data and corresponding provider data the relation data."""
        return DNSRecordRequirerData.from_relation(self.relation)

    @property
    def dns_entries(self) -> List[RequirerEntry]:
        """Fetch the DNS entries from the relation."""
        return self.dns_record_requirer_relation_data[0].dns_entries

    @property
    def processed_entries(self) -> List[DNSProviderData]:
        """Fetch the processed DNS entries."""
        return self.dns_record_requirer_relation_data[1].dns_entries


class DNSRecordRequiresEvents(ops.CharmEvents):
    """DNS record requirer events.

    This class defines the events that a DNS record requirer can emit.

    Attributes:
        dns_record_request_processed: the DNSRecordRequestProcessed.
    """

    dns_record_request_processed = ops.EventSource(DNSRecordRequestProcessed)


class DNSRecordRequires(ops.Object):
    """Requirer side of the DNS requires relation.

    Attributes:
        on: events the provider can emit.
    """

    on = DNSRecordRequiresEvents()

    def __init__(self, charm: ops.CharmBase, relation_name: str = DEFAULT_RELATION_NAME) -> None:
        """Construct.

        Args:
            charm: the provider charm.
            relation_name: the relation name.
        """
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name
        self.framework.observe(charm.on[relation_name].relation_changed, self._on_relation_changed)

    def get_remote_relation_data(self) -> Optional[DNSRecordProviderData]:
        """Retrieve the remote relation data.

        Returns:
            DNSRecordProviderData: the relation data.
        """
        relation = self.model.get_relation(self.relation_name)
        return self._get_remote_relation_data(relation) if relation else None

    def _get_remote_relation_data(self, relation: ops.Relation) -> DNSRecordProviderData:
        """Retrieve the remote relation data.

        Args:
            relation: the relation to retrieve the data from.

        Returns:
            DNSRecordProviderData: the relation data.
        """
        return DNSRecordProviderData.from_relation(relation)

    def _is_remote_relation_data_valid(self, relation: ops.Relation) -> bool:
        """Validate the relation data.

        Args:
            relation: the relation to validate.

        Returns:
            true: if the relation data is valid.
        """
        try:
            _ = self._get_remote_relation_data(relation)
            return True
        except ValueError as ex:
            logger.warning("Error validation the relation data %s", ex)
            return False

    def _on_relation_changed(self, event: ops.RelationChangedEvent) -> None:
        """Event emitted when the relation has changed.

        Args:
            event: event triggering this handler.
        """
        assert event.relation.app
        relation_data = event.relation.data[event.relation.app]
        if relation_data and self._is_remote_relation_data_valid(event.relation):
            self.on.dns_record_request_processed.emit(
                event.relation, app=event.app, unit=event.unit
            )

    def update_relation_data(
        self,
        relation: ops.Relation,
        dns_record_requirer_data: DNSRecordRequirerData,
    ) -> None:
        """Update the relation data.

        Args:
            relation: the relation for which to update the data.
            dns_record_requirer_data: DNSRecordRequirerData wrapping the data to be updated.
        """
        relation_data = dns_record_requirer_data.to_relation_data()
        relation.data[self.charm.model.app].update(relation_data)


class DNSRecordProvidesEvents(ops.CharmEvents):
    """DNS record provider events.

    This class defines the events that a DNS record provider can emit.

    Attributes:
        dns_record_request_received: the DNSRecordRequestReceived.
    """

    dns_record_request_received = ops.EventSource(DNSRecordRequestReceived)


class DNSRecordProvides(ops.Object):
    """Provider side of the DNS record relation.

    Attributes:
        on: events the provider can emit.
    """

    on = DNSRecordProvidesEvents()

    def __init__(self, charm: ops.CharmBase, relation_name: str = DEFAULT_RELATION_NAME) -> None:
        """Construct.

        Args:
            charm: the provider charm.
            relation_name: the relation name.
        """
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name
        self.framework.observe(charm.on[relation_name].relation_changed, self._on_relation_changed)

    def get_remote_relation_data(
        self,
    ) -> List[Tuple[DNSRecordRequirerData, DNSRecordProviderData]]:
        """Retrieve all the remote relations data.

        Returns:
            the relation data and the processed entries for it.
        """
        relations_data: List[Tuple[DNSRecordRequirerData, DNSRecordProviderData]] = []
        for relation in self.model.relations[self.relation_name]:
            try:
                data = self._get_remote_relation_data(relation)
            except ValueError:
                # This can happen if the relation is empty
                logger.debug("Incorrect relation data for %s", relation.id)
                continue
            except ops.model.ModelError:
                # This can happen with phantom relations
                logger.debug("ModelError for %s", relation.id)
                continue
            relations_data.append(data)
        return relations_data

    def _get_remote_relation_data(
        self, relation: ops.Relation
    ) -> Tuple[DNSRecordRequirerData, DNSRecordProviderData]:
        """Retrieve the remote relation data.

        Args:
            relation: the relation to retrieve the data from.

        Returns:
            the relation data and the processed entries for it.
        """
        return DNSRecordRequirerData.from_relation(relation)

    def _is_remote_relation_data_valid(self, relation: ops.Relation) -> bool:
        """Validate the relation data.

        Args:
            relation: the relation to validate.

        Returns:
            true: if the relation data is valid.
        """
        try:
            _ = self._get_remote_relation_data(relation)
            return True
        except ValueError as ex:
            logger.warning("Error validating the relation data %s", ex)
            return False

    def _on_relation_changed(self, event: ops.RelationChangedEvent) -> None:
        """Event emitted when the relation has changed.

        Args:
            event: event triggering this handler.
        """
        assert event.relation.app
        relation_data = event.relation.data[event.relation.app]
        if relation_data and self._is_remote_relation_data_valid(event.relation):
            self.on.dns_record_request_received.emit(
                event.relation, app=event.app, unit=event.unit
            )

    def update_relation_data(
        self, relation: ops.Relation, dns_record_provider_data: DNSRecordProviderData
    ) -> None:
        """Update the relation data.

        Args:
            relation: the relation for which to update the data.
            dns_record_provider_data: a DNSRecordProviderData instance wrapping the data to be
                updated.
        """
        relation_data = dns_record_provider_data.to_relation_data()
        relation.data[self.charm.model.app].update(relation_data)
