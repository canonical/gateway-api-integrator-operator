# Arm64 TLS Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the TLS action integration tests on arm64 with all deployed charms constrained to the runner architecture.

**Architecture:** Reuse the existing TLS action tests and certificate provider fixture. Make the provider deployment explicit about Ubuntu 24.04 and the current architecture, then expose `test_actions.py` as a second arm64 Spread task.

**Tech Stack:** Python 3.12, pytest, Jubilant, Spread, Juju 4

## Global Constraints

- Preserve amd64 integration coverage.
- Use `opcli.core.env.current_arch()` for deployment architecture.
- Keep changes uncommitted.

---

### Task 1: Architecture-aware certificate provider

**Files:**
- Modify: `gateway-api-integrator/tests/integration/conftest.py`
- Test: `gateway-api-integrator/tests/integration/test_fixtures.py`

**Interfaces:**
- Consumes: `current_arch() -> str` and `GATEWAY_BASE`.
- Produces: a certificate-provider deployment with matching `base` and `constraints`.

- [ ] **Step 1: Write the failing test**

Add a test that unwraps `certificate_provider_application_fixture`, stubs `current_arch()` to return `arm64`, and asserts the deploy call includes `base=GATEWAY_BASE` and `constraints={"arch": "arm64"}`.

- [ ] **Step 2: Run test to verify it fails**

Run: `tox -e integration -- tests/integration/test_fixtures.py -q`
Expected: FAIL because the certificate provider deploy lacks `base` and `constraints`.

- [ ] **Step 3: Write minimal implementation**

Pass `base=GATEWAY_BASE` and `constraints={"arch": current_arch()}` to the existing certificate-provider `juju.deploy` call.

- [ ] **Step 4: Run test to verify it passes**

Run: `tox -e integration -- tests/integration/test_fixtures.py -q`
Expected: both fixture tests PASS.

### Task 2: Schedule TLS action test on arm64

**Files:**
- Modify: `spread.yaml`

**Interfaces:**
- Consumes: `tests/integration/test_actions.py`.
- Produces: an arm64 Spread task named `test_actions`.

- [ ] **Step 1: Add the module mapping**

Add `MODULE/test_actions: tests/integration/test_actions.py` beside the existing no-TLS mapping.

- [ ] **Step 2: Validate the final change**

Run: `tox -e lint`, `tox -e static`, and `git diff --check`.
Expected: all commands exit successfully.
