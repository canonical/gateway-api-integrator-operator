# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the charm."""

import json
from unittest.mock import MagicMock, call

import ops
import pytest
from charmlibs.interfaces.tls_certificates import CertificateRequestAttributes
from charms.dns_integrator.v0.dns_record import CreateRecordRequestError
from httpx2 import Response
from lightkube.core.exceptions import ApiError
from lightkube.models.meta_v1 import Status
from ops import testing

from charm import GatewayAPICharm
from resource_manager.permission import InsufficientPermissionError
from state.charm_state import CharmState, ProxyMode
from state.tls import TLSInformationNotReadyError

from .conftest import GATEWAY_CLASS_CONFIG, TEST_EXTERNAL_HOSTNAME_CONFIG


def test_blocks_when_multiple_units_are_planned(base_state: dict) -> None:
    """Charm should block when more than one unit is planned."""
    ctx = testing.Context(GatewayAPICharm)
    base_state["planned_units"] = 2
    state = testing.State(**base_state)

    state = ctx.run(ctx.on.start(), state)

    assert state.unit_status == testing.BlockedStatus(
        "Deploying more than one unit is not supported."
    )


def test_dns_record(
    base_state: dict,
    gateway_relation: testing.Relation,
    certificates_relation: testing.Relation,
) -> None:
    """
    arrange: Charm is initialized with a mock state.
    act: Run reconcile via the start event.
    assert: The charm updates the dns-record relation with the expected DNS entries.
    """
    ctx = testing.Context(GatewayAPICharm)
    base_state["relations"].extend([gateway_relation, certificates_relation])
    state = ctx.run(ctx.on.start(), testing.State(**base_state))

    dns_relation = next(rel for rel in state.relations if rel.endpoint == "dns-record")
    dns_entry = json.loads(dns_relation.local_app_data["dns_entries"])[0]
    dns_entry.pop("uuid")
    assert dns_entry == {
        "domain": "example.com",
        "host_label": "@",
        "ttl": "600",
        "record_class": "IN",
        "record_type": "A",
        "record_data": "1.2.3.4",
    }


def test_dns_record_uses_dns_integrator_request_api(
    base_state: dict,
    monkeypatch: pytest.MonkeyPatch,
    gateway_relation: testing.Relation,
    certificates_relation: testing.Relation,
) -> None:
    """
    arrange: The charm has a DNS relation and the DNS Integrator request API is mocked.
    act: Run reconcile via the start event.
    assert: The charm creates and publishes the expected DNS record request.
    """
    record_request = MagicMock()
    create_record_request = MagicMock(return_value=record_request)
    update_dns_entries = MagicMock()
    monkeypatch.setattr(
        "charm.DNSRecordRequires.create_record_request", create_record_request, raising=False
    )
    monkeypatch.setattr(
        "charm.DNSRecordRequires.update_dns_entries", update_dns_entries, raising=False
    )
    ctx = testing.Context(GatewayAPICharm)
    base_state["relations"].extend([gateway_relation, certificates_relation])

    ctx.run(ctx.on.start(), testing.State(**base_state))

    create_record_request.assert_called_once_with("@ example.com 600 IN A 1.2.3.4")
    update_dns_entries.assert_called_once()
    record_requests, relation = update_dns_entries.call_args.args
    assert record_requests == [record_request]
    assert relation.id == next(
        rel.id for rel in base_state["relations"] if rel.endpoint == "dns-record"
    )


def test_dns_record_relation_changed_reconciles(
    base_state: dict,
    gateway_relation: testing.Relation,
    certificates_relation: testing.Relation,
) -> None:
    """
    arrange: The charm has a DNS relation representing a cross-model integration.
    act: Run reconcile via the DNS relation-changed event.
    assert: The charm publishes the expected DNS record.
    """
    ctx = testing.Context(GatewayAPICharm)
    base_state["relations"].extend([gateway_relation, certificates_relation])
    state = testing.State(**base_state)
    dns_relation = next(rel for rel in state.relations if rel.endpoint == "dns-record")

    state = ctx.run(ctx.on.relation_changed(dns_relation), state)

    dns_relation = next(rel for rel in state.relations if rel.endpoint == "dns-record")
    assert json.loads(dns_relation.local_app_data["dns_entries"])[0]["domain"] == "example.com"


def test_dns_record_blocks_without_publishing_partial_requests(
    base_state: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    arrange: A gateway-route relation provides hostnames and one request is rejected as invalid.
    act: Run reconcile via the gateway-route relation-changed event.
    assert: The charm tries all requests, publishes none, and blocks with the failed hostname.
    """
    namespace_error = CreateRecordRequestError("Namespace not found !")
    namespace_error.__cause__ = ops.SecretNotFoundError("dns-record")
    create_record_request = MagicMock(
        side_effect=[namespace_error, CreateRecordRequestError("invalid record")]
    )
    update_dns_entries = MagicMock()
    monkeypatch.setattr("charm.DNSRecordRequires.create_record_request", create_record_request)
    monkeypatch.setattr("charm.DNSRecordRequires.update_dns_entries", update_dns_entries)
    base_state["config"]["external-hostname"] = ""
    base_state["config"]["enforce-https"] = False
    gateway_route_relation = testing.Relation(
        endpoint="gateway-route",
        interface="gateway-route",
        remote_app_data={
            "hostname": json.dumps("alpha.example.com"),
            "additional_hostnames": json.dumps(["zulu.example.com"]),
        },
    )
    base_state["relations"].append(gateway_route_relation)
    ctx = testing.Context(GatewayAPICharm)

    state = ctx.run(ctx.on.relation_changed(gateway_route_relation), testing.State(**base_state))

    assert create_record_request.call_args_list == [
        call("@ alpha.example.com 600 IN A 1.2.3.4"),
        call("@ zulu.example.com 600 IN A 1.2.3.4"),
    ]
    update_dns_entries.assert_not_called()
    assert state.unit_status == ops.BlockedStatus(
        "Unable to create DNS records for: alpha.example.com, zulu.example.com"
    )


def test_dns_record_waits_for_missing_namespace(
    base_state: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    arrange: The DNS library cannot find its local record-request namespace secret.
    act: Run reconcile via the gateway-route relation-changed event.
    assert: The charm publishes no records and waits for the namespace to become available.
    """
    namespace_error = CreateRecordRequestError("Namespace not found !")
    namespace_error.__cause__ = ops.SecretNotFoundError("dns-record")
    create_record_request = MagicMock(side_effect=namespace_error)
    update_dns_entries = MagicMock()
    monkeypatch.setattr("charm.DNSRecordRequires.create_record_request", create_record_request)
    monkeypatch.setattr("charm.DNSRecordRequires.update_dns_entries", update_dns_entries)
    base_state["config"]["external-hostname"] = ""
    base_state["config"]["enforce-https"] = False
    gateway_route_relation = testing.Relation(
        endpoint="gateway-route",
        interface="gateway-route",
        remote_app_data={
            "hostname": json.dumps("example.com"),
            "additional_hostnames": json.dumps([]),
        },
    )
    base_state["relations"].append(gateway_route_relation)
    ctx = testing.Context(GatewayAPICharm)

    state = ctx.run(ctx.on.relation_changed(gateway_route_relation), testing.State(**base_state))

    create_record_request.assert_called_once_with("@ example.com 600 IN A 1.2.3.4")
    update_dns_entries.assert_not_called()
    assert state.unit_status == ops.WaitingStatus("Waiting for DNS record request namespace")


def test_dns_record_clears_entries_without_hostnames(
    base_state: dict,
    monkeypatch: pytest.MonkeyPatch,
    certificates_relation: testing.Relation,
) -> None:
    """
    arrange: The charm has a DNS relation but no managed hostnames.
    act: Run reconcile via the start event.
    assert: The charm publishes an empty request list to clear stale DNS entries.
    """
    create_record_request = MagicMock()
    update_dns_entries = MagicMock()
    monkeypatch.setattr("charm.DNSRecordRequires.create_record_request", create_record_request)
    monkeypatch.setattr("charm.DNSRecordRequires.update_dns_entries", update_dns_entries)
    base_state["config"]["external-hostname"] = ""
    base_state["relations"].append(certificates_relation)
    ctx = testing.Context(GatewayAPICharm)

    ctx.run(ctx.on.start(), testing.State(**base_state))

    create_record_request.assert_not_called()
    update_dns_entries.assert_called_once()
    assert update_dns_entries.call_args.args[0] == []


def test_dns_record_no_gateway_resource(
    base_state: dict,
    monkeypatch: pytest.MonkeyPatch,
    gateway_relation: testing.Relation,
    certificates_relation: testing.Relation,
) -> None:
    """
    arrange: Charm is initialized with a mock state without a gateway resource.
    act: Run reconcile via the start event.
    assert: The charm does not update the dns-record relation.
    """
    monkeypatch.setattr(
        "charm.GatewayResourceManager.current_gateway_resource",
        lambda self: None,
    )
    ctx = testing.Context(GatewayAPICharm)
    base_state["relations"].append(gateway_relation)
    base_state["relations"].append(certificates_relation)
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.start(), state)
    assert "dns_entries" not in next(iter(state.relations)).local_app_data


def test_dns_record_no_gateway_address(
    base_state: dict,
    monkeypatch: pytest.MonkeyPatch,
    gateway_relation: testing.Relation,
    certificates_relation: testing.Relation,
) -> None:
    """
    arrange: Charm is initialized with a mock state without a gateway address.
    act: Run reconcile via the start event.
    assert: The charm does not update the dns-record relation.
    """
    monkeypatch.setattr("charm.GatewayResourceManager.gateway_address", lambda self, name: None)
    ctx = testing.Context(GatewayAPICharm)
    base_state["relations"].append(gateway_relation)
    base_state["relations"].append(certificates_relation)
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.start(), state)
    assert "dns_entries" not in next(iter(state.relations)).local_app_data


def test_gateway_route(
    base_state: dict,
    monkeypatch: pytest.MonkeyPatch,
    gateway_route_relation: testing.Relation,
    certificates_relation: testing.Relation,
) -> None:
    """
    arrange: Charm is initialized with a mock state.
    act: Run reconcile via the relation_changed event.
    assert: The charm updates the dns-record relation with the expected DNS entries
        and publishes provider data to gateway-route relation.
    """
    # external-hostname is ingress-only; clear it for gateway-route mode.
    base_state["config"]["external-hostname"] = ""
    ctx = testing.Context(GatewayAPICharm)
    base_state["relations"].append(gateway_route_relation)
    base_state["relations"].append(certificates_relation)
    state = testing.State(**base_state)
    gateway_route_relation = next(
        rel for rel in state.relations if rel.endpoint == "gateway-route"
    )
    state = ctx.run(ctx.on.relation_changed(gateway_route_relation), state)
    dns_relation = next(rel for rel in state.relations if rel.endpoint == "dns-record")
    dns_entry = json.loads(dns_relation.local_app_data["dns_entries"])[0]
    dns_entry.pop("uuid")
    assert dns_entry == {
        "domain": "example.com",
        "host_label": "@",
        "ttl": "600",
        "record_class": "IN",
        "record_type": "A",
        "record_data": "1.2.3.4",
    }

    # Verify provider data is published to gateway-route relation
    gw_route_rel = next(rel for rel in state.relations if rel.endpoint == "gateway-route")
    assert "gateway_name" in gw_route_rel.local_app_data
    assert "gateway_model" in gw_route_rel.local_app_data
    assert "https_mode" in gw_route_rel.local_app_data


def test_blocked_when_relation_integrated_without_hostname(
    base_state: dict,
    gateway_relation: testing.Relation,
    certificates_relation: testing.Relation,
) -> None:
    """Charm should block when ingress is integrated but no hostname can be derived."""
    ctx = testing.Context(GatewayAPICharm)
    base_state["config"]["external-hostname"] = ""
    base_state["relations"].append(gateway_relation)
    base_state["relations"].append(certificates_relation)
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.start(), state)

    assert state.unit_status.name == ops.BlockedStatus.name
    assert "external-hostname must be set" in state.unit_status.message


def test_get_certificate_requests_includes_gateway_ip_when_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    arrange: Charm state requires an IP certificate and gateway address is known.
    act: Call _get_certificate_requests directly.
    assert: Certificate requests include an IP SAN CSR for the gateway address.
    """
    monkeypatch.setattr(
        "charm.CharmState.from_charm_and_providers",
        MagicMock(
            return_value=CharmState(
                gateway_class_name=GATEWAY_CLASS_CONFIG,
                enforce_https=True,
                proxy_mode=ProxyMode.GATEWAY_ROUTE,
                requires_ip_certificate=True,
                hsts_max_age=31536000,
                hostnames=set(),
            )
        ),
    )

    mock_self = MagicMock()
    mock_self._current_gateway_address.return_value = "1.2.3.4"
    csrs = GatewayAPICharm._get_certificate_requests(mock_self)

    ip_csrs = [c for c in csrs if isinstance(c, CertificateRequestAttributes) and c.sans_ip]
    assert len(ip_csrs) == 1
    assert ip_csrs[0].common_name == "1.2.3.4"
    assert ip_csrs[0].sans_ip is not None
    assert "1.2.3.4" in ip_csrs[0].sans_ip


def test_gateway_route_with_invalid_data_not_blocked(
    base_state: dict,
    monkeypatch: pytest.MonkeyPatch,
    certificates_relation: testing.Relation,
) -> None:
    """Charm should not block when all gateway-route relations provide invalid data."""
    invalid_gateway_route_relation = testing.Relation(
        endpoint="gateway-route",
        interface="gateway-route",
        remote_app_data={},
    )

    ctx = testing.Context(GatewayAPICharm)
    base_state["config"]["external-hostname"] = ""
    base_state["relations"].append(invalid_gateway_route_relation)
    base_state["relations"].append(certificates_relation)
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.start(), state)

    assert state.unit_status.name != ops.BlockedStatus.name


def test_waiting_when_tls_information_not_ready_still_runs_gateway_definition(
    base_state: dict,
    monkeypatch: pytest.MonkeyPatch,
    certificates_relation: testing.Relation,
) -> None:
    """When TLS is pending, reconcile should still define gateway and end in waiting status."""
    define_gateway_resource_mock = MagicMock()
    monkeypatch.setattr(
        "charm.GatewayAPICharm._define_gateway_resource", define_gateway_resource_mock
    )
    monkeypatch.setattr(
        "state.tls.TLSInformation.from_charm",
        MagicMock(
            side_effect=TLSInformationNotReadyError("Waiting for TLS certificates to be issued.")
        ),
    )

    ctx = testing.Context(GatewayAPICharm)
    base_state["relations"].append(certificates_relation)
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.start(), state)

    define_gateway_resource_mock.assert_called_once()
    assert state.unit_status.name == ops.WaitingStatus.name
    assert state.unit_status.message == "Waiting for TLS certificates to be issued."


def test_waiting_when_ip_san_certificate_missing(
    base_state: dict,
    monkeypatch: pytest.MonkeyPatch,
    certificates_relation: testing.Relation,
) -> None:
    """Reconcile should wait when hostname cert exists but required IP SAN cert is missing."""
    monkeypatch.setattr(
        "charm.CharmState.from_charm_and_providers",
        MagicMock(
            return_value=CharmState(
                gateway_class_name=GATEWAY_CLASS_CONFIG,
                enforce_https=True,
                proxy_mode=ProxyMode.INGRESS,
                requires_ip_certificate=True,
                hsts_max_age=31536000,
                hostnames={"example.com"},
            )
        ),
    )

    ctx = testing.Context(GatewayAPICharm)
    base_state["relations"].append(certificates_relation)
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.start(), state)

    assert state.unit_status.name == ops.WaitingStatus.name
    assert state.unit_status.message == "Waiting for TLS certificates to be issued."


@pytest.mark.usefixtures("client_with_mock_external")
def test_get_certificate_requests_uses_configured_common_name_instead_of_hostname(
    gateway_relation: testing.Relation,
    certificates_relation: testing.Relation,
) -> None:
    """Configured CSR subject attributes should be propagated into generated CSRs."""
    ctx = testing.Context(GatewayAPICharm)
    state_in = testing.State(
        leader=True,
        config={
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
            "csr-subject-attributes": (
                "C=DE, ST=Hesse, L=Frankfurt, O=Canonical, "
                "OU=Engineering, CN=csr.example.com, emailAddress=ops@example.com"
            ),
        },
        relations=[gateway_relation, certificates_relation],
    )

    with ctx(ctx.on.update_status(), state_in) as manager:
        csrs = manager.charm._get_certificate_requests()

    assert len(csrs) == 1
    csr = csrs[0]
    assert csr.common_name == "csr.example.com"
    assert csr.sans_dns is not None
    assert "example.com" in csr.sans_dns
    assert csr.country_name == "DE"
    assert csr.state_or_province_name == "Hesse"
    assert csr.locality_name == "Frankfurt"
    assert csr.organization == "Canonical"
    assert csr.organizational_unit == "Engineering"
    assert csr.email_address == "ops@example.com"


@pytest.mark.usefixtures("client_with_mock_external")
def test_get_certificate_requests_uses_default_cn_when_not_set(
    gateway_relation: testing.Relation,
    certificates_relation: testing.Relation,
) -> None:
    """Hostname should remain CSR common_name when custom CN is not configured."""
    ctx = testing.Context(GatewayAPICharm)
    state_in = testing.State(
        leader=True,
        config={
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
            "csr-subject-attributes": "C=DE, ST=Hesse, O=Canonical",
        },
        relations=[gateway_relation, certificates_relation],
    )

    with ctx(ctx.on.update_status(), state_in) as manager:
        csrs = manager.charm._get_certificate_requests()

    assert len(csrs) == 1
    assert csrs[0].common_name == "example.com"


def test_invalid_custom_csr_subject_attributes_blocks_charm(
    base_state: dict,
    certificates_relation: testing.Relation,
) -> None:
    """Invalid custom CSR subject attributes should put charm in blocked state."""
    ctx = testing.Context(GatewayAPICharm)
    base_state["config"]["csr-subject-attributes"] = "foo=bar"
    base_state["relations"].append(certificates_relation)
    state_in = testing.State(**base_state)

    state_out = ctx.run(ctx.on.config_changed(), state_in)

    assert state_out.unit_status == ops.BlockedStatus(
        'invalid "csr-subject-attributes" value; see logs.'
    )


@pytest.mark.usefixtures("client_with_mock_external")
def test_deploy_invalid_config(certificates_relation: testing.Relation) -> None:
    """
    arrange: given a leader charm related to a TLS provider but with no gateway-class configured.
    act: run the config-changed event.
    assert: the charm goes into blocked state.
    """
    ctx = testing.Context(GatewayAPICharm)
    state_in = testing.State(leader=True, relations=[certificates_relation])

    state_out = ctx.run(ctx.on.config_changed(), state_in)

    assert state_out.unit_status.name == ops.BlockedStatus.name


@pytest.mark.usefixtures("client_with_mock_external")
def test_deploy_missing_tls() -> None:
    """
    arrange: given a leader charm with valid config but no certificates relation.
    act: run the config-changed event.
    assert: the charm blocks asking for the certificates relation.
    """
    ctx = testing.Context(GatewayAPICharm)
    state_in = testing.State(
        leader=True,
        config={
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        },
    )

    state_out = ctx.run(ctx.on.config_changed(), state_in)

    assert state_out.unit_status == ops.BlockedStatus(
        "Certificates relation is required when enforce-https is enabled."
    )


@pytest.mark.parametrize(
    "error_code",
    [
        pytest.param(401, id="unauthorized"),
        pytest.param(400, id="bad request"),
        pytest.param(404, id="not found"),
    ],
)
def test_reconcile_api_error_4xx(
    client_with_mock_external: MagicMock,
    gateway_relation: testing.Relation,
    certificates_relation: testing.Relation,
    monkeypatch: pytest.MonkeyPatch,
    error_code: int,
) -> None:
    """
    arrange: given a valid charm whose k8s client raises a non-403 ApiError on create.
    act: run the config-changed event.
    assert: the ApiError propagates out of the charm.
    """
    monkeypatch.setattr(
        "lightkube.models.meta_v1.Status.from_dict",
        MagicMock(return_value=Status(code=error_code)),
    )
    monkeypatch.setattr(
        "resource_manager.gateway.GatewayResourceManager.current_gateway_resource",
        MagicMock(return_value=None),
    )
    client_with_mock_external.create.side_effect = ApiError(response=MagicMock(spec=Response))
    ctx = testing.Context(GatewayAPICharm)
    state_in = testing.State(
        leader=True,
        config={
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        },
        relations=[gateway_relation, certificates_relation],
    )

    with pytest.raises(testing.errors.UncaughtCharmError) as exc_info:
        ctx.run(ctx.on.config_changed(), state_in)
    assert isinstance(exc_info.value.__cause__, ApiError)


def test_reconcile_api_error_forbidden(
    client_with_mock_external: MagicMock,
    gateway_relation: testing.Relation,
    certificates_relation: testing.Relation,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    arrange: given a valid charm whose k8s client raises a 403 ApiError on create.
    act: run the config-changed event.
    assert: the charm goes into blocked state asking for `juju trust`.
    """
    monkeypatch.setattr(
        "lightkube.models.meta_v1.Status.from_dict",
        MagicMock(return_value=Status(code=403)),
    )
    monkeypatch.setattr(
        "resource_manager.gateway.GatewayResourceManager.current_gateway_resource",
        MagicMock(return_value=None),
    )
    client_with_mock_external.create.side_effect = ApiError(response=MagicMock(spec=Response))
    ctx = testing.Context(GatewayAPICharm)
    state_in = testing.State(
        leader=True,
        config={
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        },
        relations=[gateway_relation, certificates_relation],
    )

    state_out = ctx.run(ctx.on.config_changed(), state_in)

    assert state_out.unit_status.name == ops.BlockedStatus.name
    assert "juju trust" in state_out.unit_status.message


@pytest.mark.usefixtures("client_with_mock_external")
def test_create_http_route_insufficient_permission(
    gateway_relation: testing.Relation,
    certificates_relation: testing.Relation,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    arrange: given a valid charm whose HTTPRoute resource manager raises a permission error.
    act: run the config-changed event.
    assert: the charm goes into blocked state.
    """
    monkeypatch.setattr(
        "resource_manager.http_route.HTTPRouteResourceManager.define_resource",
        MagicMock(side_effect=InsufficientPermissionError),
    )
    monkeypatch.setattr(
        "resource_manager.gateway.GatewayResourceManager.current_gateway_resource",
        MagicMock(return_value=None),
    )
    ctx = testing.Context(GatewayAPICharm)
    state_in = testing.State(
        leader=True,
        config={
            "external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
            "gateway-class": GATEWAY_CLASS_CONFIG,
        },
        relations=[gateway_relation, certificates_relation],
    )

    state_out = ctx.run(ctx.on.config_changed(), state_in)

    assert state_out.unit_status.name == ops.BlockedStatus.name
