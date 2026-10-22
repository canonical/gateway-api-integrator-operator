# Arm64 Smoke Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the existing no-TLS proxied-endpoints integration test on amd64 and arm64 while retaining the full integration suite on amd64.

**Architecture:** Replace the amd64-only `flask-k8s` fixture with plain `any-charm:beta`, injecting the repository's ingress library and a detached Python standard-library HTTP server that runs directly on the charm unit. Add arm64 charm build metadata and a restricted Spread suite that explicitly selects only `test_actions_no_tls.py`, following Traefik's established pattern.

**Tech Stack:** Python 3.12, Jubilant, any-charm, canonical/charm-ci opcli, Spread, Charmcraft.

## Global Constraints

- Keep all changes uncommitted.
- Do not use `any-charm-k8s` or a workload container.
- Do not run e2e tests on arm64 because `ingress-configurator` is not migrated.
- Keep the full integration suite amd64-only.
- Run only `test_actions_no_tls.py` in the arm64 suite.
- Preserve existing HTTP response assertions in the amd64 integration suite.

---

### Task 1: Architecture-neutral ingress test backend

**Files:**
- Create: `gateway-api-integrator/tests/integration/ingress_requirer.py`
- Modify: `gateway-api-integrator/tests/integration/conftest.py`
- Modify: `gateway-api-integrator/tests/integration/test_charm_ingress_interface.py`
- Modify: `gateway-api-integrator/tests/integration/test_tls.py`

**Interfaces:**
- Produces: an `AnyCharm.start_server()` RPC method serving `Hello from any-charm` on port 8080.
- Consumes: `IngressPerAppRequirer` from the repository's ingress library.

- [ ] Add the injected any-charm implementation using `python3 -m http.server`, `start_new_session=True`, a PID file, and a model/application-specific response file.
- [ ] Deploy plain `any-charm` on `ubuntu@24.04` through `latest/beta`, inject `any_charm.py` and `ingress.py`, wait for active, and invoke `start_server` through the RPC action.
- [ ] Remove the unnecessary certificate-provider dependency from the no-TLS configured fixture.
- [ ] Update backend body assertions from the flask-specific text to `Hello from any-charm`.
- [ ] Run `tox -e lint` in `gateway-api-integrator/`.
- [ ] Run the focused amd64 Spread selector for `test_actions_no_tls`.

### Task 2: Restricted arm64 Spread job

**Files:**
- Modify: `gateway-api-integrator/charmcraft.yaml`
- Modify: `artifacts.yaml`
- Modify: `spread.yaml`

**Interfaces:**
- Produces: an arm64 charm artifact and one arm64 Spread job for `test_actions_no_tls.py`.

- [ ] Add `arm64` to the charm's supported platforms and artifact matrix.
- [ ] Add the `ubuntu-24.04-arm64` Spread system with `runner: [ubuntu-24.04-arm]` and `arch: arm64`.
- [ ] Restrict the existing full suite to `ubuntu-24.04`.
- [ ] Add an explicit arm64 suite with `auto-discover: false` and `MODULE/test_actions_no_tls`.
- [ ] Run `opcli artifacts jobs` and verify amd64 and arm64 builds.
- [ ] Run `opcli spread jobs` and verify exactly one arm64 integration task plus the existing amd64/e2e tasks.
- [ ] Run repository lint checks and leave all changes uncommitted.
