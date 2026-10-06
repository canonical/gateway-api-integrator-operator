# DNS Record Relation Modernization Design

## Goal

Modernize the gateway API integrator charm's existing `dns-record` requirer to use the current canonical `charms.dns_integrator.v0.dns_record` library and verify that requested records resolve through a real Bind provider.

## Scope

- Preserve the optional `dns-record` endpoint and its `dns_record` wire interface.
- Publish one A record with TTL 600 for every hostname in `CharmState.hostnames`.
- Point each record at the current Gateway load-balancer IPv4 address.
- Refresh the complete request set when hostnames or the Gateway address change.
- Clear stale DNS requests when the managed hostname set becomes empty.
- Keep DNS integration optional: an absent or removed relation must not affect charm status.
- Do not add support for provider-allocated DDNS domains or AAAA records in this change.

## Vendored Library

Vendor the unpublished canonical library at:

`gateway-api-integrator/lib/charms/dns_integrator/v0/dns_record.py`

Source:

- Repository: `canonical/dns-operators`
- Path: `dns-integrator-operator/lib/charms/dns_integrator/v0/dns_record.py`
- Commit: `599941369b1809292a5f654049387a52408c0a6f`
- Library version: `LIBAPI = 0`, `LIBPATCH = 2`

The file remains an unmodified vendored library. Its header and library metadata provide provenance; the implementation plan must use the pinned commit instead of `main`. The library is not declared under `charm-libs` because it is not available from Charmhub.

Remove the superseded vendored `charms.bind.v0.dns_record` library after all imports and tests use the new path.

## Charm Design

Keep DNS orchestration in `GatewayAPICharm`; do not introduce a separate `src/dns_record.py` service.

The charm instantiates `DNSRecordRequires` from `charms.dns_integrator.v0.dns_record`. Existing `dns-record` relation-created and relation-joined handlers continue to call the main reconciliation loop.

`_update_dns_record_relation` retains responsibility for determining whether publishing is possible:

1. Return immediately on non-leader units because application relation data is leader-owned.
2. Return when no `dns-record` relation exists.
3. Return with a warning when the Gateway resource or Gateway address is not ready.
4. For each sorted managed hostname, call `create_record_request("@ <hostname> 600 IN A <address>")`.
5. Log and skip an individual hostname when `CreateRecordRequestError` is raised.
6. Call `update_dns_entries(entries, relation)` with all valid requests, including an empty list when no hostnames remain, so stale requests are removed.

The library owns deterministic request UUID generation through its Juju-secret namespace. The charm's custom UUID namespace and manual `RecordRequest` construction are removed.

## Error Handling

Invalid individual record requests are non-fatal and produce warning logs. If every hostname is invalid, the charm publishes an empty request list so previous records are withdrawn.

Missing relations and not-yet-assigned Gateway addresses are normal readiness states and do not block the charm. Unexpected model errors from writing relation data are allowed to propagate through the existing reconciliation and status handling rather than being silently discarded.

## Testing

### Local Tests

Use the repository's tox environments for all local checks:

- `tox -e unit -- tests/unit/test_charm.py -k dns_record`
- `tox -e unit`
- `tox -e lint`
- `tox -e static`

Focused unit coverage verifies:

- A request is generated for each sorted hostname and published with `update_dns_entries`.
- The charm does not publish without a relation, Gateway resource, or Gateway address.
- Non-leaders do not write application relation data.
- Invalid hostnames are skipped without preventing valid requests.
- An empty hostname set publishes an empty list and clears stale requests.
- Relation-created and relation-joined events reconcile the DNS data.

### Integration Tests

Replace the any-charm databag assertion with Bind-backed behavior tests. Add a fixture that deploys `bind`/`bind-operator`, integrates its `dns-record` endpoint, and waits for active status.

The integration suite verifies:

- `gateway.internal` resolves through Bind to the Gateway load-balancer address.
- Changing the configured external hostname publishes a resolvable replacement record.
- Removing the `dns-record` relation leaves gateway-api-integrator active.

Run deployed integration tests through the repository's opcli/Spread workflow, which expands the suite to `tox -e integration`. Do not invoke the integration pytest module directly outside opcli.

## Terraform And Documentation

The Terraform charm module already exposes the `dns_record` requires endpoint, so no Terraform interface change is needed. No user documentation change is required because the external endpoint and relation contract remain unchanged.