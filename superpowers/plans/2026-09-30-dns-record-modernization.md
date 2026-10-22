# DNS Record Relation Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the legacy Bind-specific DNS relation library with the current canonical DNS Integrator library and verify requested records through a real Bind deployment.

**Architecture:** Vendor the unpublished canonical library at a pinned upstream commit and keep DNS orchestration inside `GatewayAPICharm._update_dns_record_relation`. The charm converts all managed hostnames into library-owned deterministic `RecordRequest` objects and publishes the complete set through `update_dns_entries`, while the integration suite verifies actual DNS resolution.

**Tech Stack:** Python 3.12, Ops 3, Pydantic 2, Jubilant, tox, opcli/Spread, Bind operator

## Global Constraints

- Vendor `canonical/dns-operators` commit `599941369b1809292a5f654049387a52408c0a6f` without modifying the library source.
- Keep the `dns-record` endpoint optional and wire-compatible with interface `dns_record`.
- Publish A records only, with host label `@` and TTL 600.
- Use `tox -e <environment>` for local test and quality commands.
- Run deployed integration tests through opcli/Spread, not by invoking integration pytest directly.
- Do not add a `src/dns_record.py` service.

---

### Task 1: Vendor The Canonical Library

**Files:**
- Create: `gateway-api-integrator/lib/charms/dns_integrator/v0/dns_record.py`
- Delete: `gateway-api-integrator/lib/charms/bind/v0/dns_record.py`

**Interfaces:**
- Consumes: canonical source at commit `599941369b1809292a5f654049387a52408c0a6f`
- Produces: `DNSRecordRequires`, `CreateRecordRequestError`, and `RecordRequest` under `charms.dns_integrator.v0.dns_record`

- [ ] **Step 1: Copy the pinned upstream file unchanged**

Fetch the exact raw source from:

```text
https://raw.githubusercontent.com/canonical/dns-operators/599941369b1809292a5f654049387a52408c0a6f/dns-integrator-operator/lib/charms/dns_integrator/v0/dns_record.py
```

Store it at `gateway-api-integrator/lib/charms/dns_integrator/v0/dns_record.py` without edits.

- [ ] **Step 2: Verify the vendored file matches upstream**

Run:

```bash
diff -u \
  <(curl -fsSL https://raw.githubusercontent.com/canonical/dns-operators/599941369b1809292a5f654049387a52408c0a6f/dns-integrator-operator/lib/charms/dns_integrator/v0/dns_record.py) \
  gateway-api-integrator/lib/charms/dns_integrator/v0/dns_record.py
```

Expected: no output and exit code 0.

- [ ] **Step 3: Remove the superseded library**

Delete `gateway-api-integrator/lib/charms/bind/v0/dns_record.py` after all production imports are migrated in Task 2. Empty namespace directories may remain because Python namespace packages do not require `__init__.py` files.

### Task 2: Migrate Charm DNS Publishing

**Files:**
- Modify: `gateway-api-integrator/src/charm.py`
- Test: `gateway-api-integrator/tests/unit/test_charm.py`

**Interfaces:**
- Consumes: `DNSRecordRequires.create_record_request(data: Iterable[str] | str) -> RecordRequest`
- Consumes: `DNSRecordRequires.update_dns_entries(record_requests: list[RecordRequest], relation: ops.Relation | None = None) -> None`
- Produces: `_update_dns_record_relation(..., hostnames: Collection[str]) -> None`

- [ ] **Step 1: Update focused unit expectations first**

Replace assertions tied to manually serialized UUID values with behavior assertions that patch `DNSRecordRequires.create_record_request` and `update_dns_entries`. Cover sorted hostnames, non-leader behavior, invalid requests, empty hostnames, missing Gateway resources, and missing Gateway addresses.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run from `gateway-api-integrator/`:

```bash
tox -e unit -- tests/unit/test_charm.py -k dns_record
```

Expected: FAIL because the charm still imports `charms.bind.v0` and calls the old data-model API.

- [ ] **Step 3: Replace imports and request construction**

Import `CreateRecordRequestError`, `DNSRecordRequires`, and `RecordRequest` from `charms.dns_integrator.v0.dns_record`. Remove the manual UUID namespace and old data-model imports.

In `_update_dns_record_relation`:

1. Return for a non-leader or absent relation.
2. Keep the existing Gateway resource/address readiness checks.
3. Call `create_record_request("@ <hostname> 600 IN A <address>")` for each sorted hostname.
4. Log and skip `CreateRecordRequestError` for an individual hostname.
5. Call `update_dns_entries(entries, relation)`, including when `entries` is empty.

- [ ] **Step 4: Run focused tests**

Run:

```bash
tox -e unit -- tests/unit/test_charm.py -k dns_record
```

Expected: all selected tests PASS.

- [ ] **Step 5: Remove the old vendored library and run all unit tests**

Run:

```bash
tox -e unit
```

Expected: PASS with no import of `charms.bind.v0.dns_record`.

### Task 3: Verify Real DNS Resolution

**Files:**
- Modify: `gateway-api-integrator/tests/integration/conftest.py`
- Modify: `gateway-api-integrator/tests/integration/test_charm_dns.py`

**Interfaces:**
- Consumes: Jubilant `Juju.deploy`, `Juju.integrate`, `Juju.exec`, `Juju.config`, and `Juju.remove_relation`
- Produces: module-scoped `bind_operator` fixture returning the deployed application name

- [ ] **Step 1: Add the Bind fixture**

Add constants for the Bind charm name and tested channel, then add a module-scoped fixture that deploys Bind, integrates `gateway-api-integrator:dns-record` with `bind:dns-record`, and waits until both applications are active. Follow the deployment form used by the pinned HAProxy reference while keeping names consistent with this repository.

- [ ] **Step 2: Replace databag inspection with resolver helpers**

Add a helper to select a reachable unit address and a helper that runs `dig +short @<nameserver> <hostname> A` through `Juju.exec`. Remove the `any-charm`, `show-unit`, Juju-version branching, and direct JSON databag assertions.

- [ ] **Step 3: Add resolution and lifecycle tests**

Implement tests that:

- Resolve `gateway.internal` through Bind and assert the Gateway load-balancer address is returned.
- Change `external-hostname`, wait, and assert the replacement hostname resolves.
- Remove the relation and assert gateway-api-integrator remains active.

Derive the expected address from the Gateway service/load-balancer state already available to the integration suite, not from the gateway charm pod address.

- [ ] **Step 4: Run the integration module through opcli/Spread**

Use the repository Spread suite, which executes:

```bash
opcli pytest expand --suite "$OPCLI_SUITE" --module tests/integration/test_charm_dns.py -e integration
```

Run the generated command through the existing `gateway-api-integrator/tests/integration-juju4/` Spread task. Expected: the Bind resolution, hostname update, and relation-removal tests PASS on Juju 4.

### Task 4: Final Quality Checks

**Files:**
- Verify all files changed in Tasks 1-3

**Interfaces:**
- Consumes: completed implementation
- Produces: validated change ready for review

- [ ] **Step 1: Run lint**

Run from `gateway-api-integrator/`:

```bash
tox -e lint
```

Expected: PASS.

- [ ] **Step 2: Run static analysis**

Run:

```bash
tox -e static
```

Expected: PASS.

- [ ] **Step 3: Run the full unit suite**

Run:

```bash
tox -e unit
```

Expected: PASS.

- [ ] **Step 4: Confirm no legacy imports remain**

Run from the repository root:

```bash
grep -R "charms.bind.v0.dns_record" gateway-api-integrator/src gateway-api-integrator/tests || true
```

Expected: no output.

- [ ] **Step 5: Review the final diff**

Run:

```bash
git diff --check
git diff --stat
```

Expected: no whitespace errors; only the vendored library migration, charm DNS logic, tests, design, and plan are changed.
