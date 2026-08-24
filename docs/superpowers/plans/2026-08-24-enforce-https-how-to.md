# Enforce HTTPS How-To Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a how-to guide that explains how to enable/disable HTTPS enforcement (`enforce-https`) for the `gateway-api-integrator` charm, including that it is enforced by default, how to turn it off, and the consequences.

**Architecture:** Add one new MyST Markdown page under `docs/how-to/`, register it in the how-to `toctree` and the documentation landing page, then verify the Sphinx build produces no warnings and passes the project's doc linters. This mirrors the existing `docs/how-to/select-gateway-class.md` guide.

**Tech Stack:** Sphinx + MyST Markdown, the project's `docs/Makefile` targets (`make html`, `make linkcheck`, `make vale`), Read the Docs for publication.

## Global Constraints

- Page files live in `docs/how-to/` and use MyST Markdown (`.md`).
- Every guide page starts with an `html_meta` frontmatter `description lang=en` block, copied style-for-style from [docs/how-to/select-gateway-class.md](docs/how-to/select-gateway-class.md).
- Every guide page declares a MyST target anchor in the form `(how_to_<slug>)=` immediately after the frontmatter so it can be cross-referenced with `{ref}`.
- Config-option facts must match the charm's `charmcraft.yaml`: the option is named `enforce-https`, type `boolean`, `default: true`.
- Behavioural facts must match the charm source: when `enforce-https=true` a `certificates` (`tls-certificates`) relation is REQUIRED or the charm blocks with the message `Certificates relation is required when enforce-https is enabled.`
- Do NOT introduce broken `{ref}` cross-references. Only link to anchors that already exist (`how_to_index`, `how_to_select_gateway_class`, `tutorial_using_gateway_route`). Mention `hsts-max-age` by name in prose (no `{ref}` link, since no HSTS guide exists yet).
- Commit messages use Conventional Commits (`docs: ...`), matching the repository history.

---

### Task 1: Author and publish the `enforce-https` how-to guide

**Files:**
- Create: `docs/how-to/enforce-https.md`
- Modify: `docs/how-to/index.md` (the `toctree` block)
- Modify: `docs/index.md` (the "Deployment" row of the landing-page `list-table`)

**Interfaces:**
- Consumes: the existing MyST target anchors `how_to_index` (in [docs/how-to/index.md](docs/how-to/index.md)) and `how_to_select_gateway_class` (in [docs/how-to/select-gateway-class.md](docs/how-to/select-gateway-class.md)) — these are the only cross-references the new page and landing page rely on.
- Produces: a new MyST target anchor `how_to_enforce_https`, defined in `docs/how-to/enforce-https.md`, that later docs work can reference with `{ref}\`how_to_enforce_https\``.

- [ ] **Step 1: Create the guide page**

Create `docs/how-to/enforce-https.md` with exactly this content:

````markdown
---
myst:
  html_meta:
    "description lang=en": "Learn how to enable or disable HTTPS enforcement for the gateway-api-integrator charm"
---

(how_to_enforce_https)=

# How to enforce HTTPS

The `enforce-https` configuration option controls whether the `gateway-api-integrator` charm
redirects plain HTTP traffic to HTTPS. It is a boolean option and is **enabled by default**
(`enforce-https=true`), so HTTPS is enforced unless you explicitly turn it off.

When HTTPS is enforced, the charm:

- Requires an integration with a TLS certificates provider through the `certificates` relation.
- Serves an HTTP listener that issues a `301` redirect to HTTPS, alongside the HTTPS listener.
- Injects a `Strict-Transport-Security` (HSTS) header on HTTPS responses, controlled by the
  `hsts-max-age` configuration option.

```{caution}
While `enforce-https` is `true`, the charm needs a `certificates` relation. If none is present,
the charm goes into a blocked state with the message
`Certificates relation is required when enforce-https is enabled.`
When related via `ingress`, the `external-hostname` configuration option must also be set.
```

## Keep HTTPS enforced (default)

No action is required to keep HTTPS enforced: `enforce-https` defaults to `true`. Provide a TLS
provider and, in `ingress` mode, an external hostname:

```bash
juju integrate gateway-api-integrator self-signed-certificates
juju config gateway-api-integrator external-hostname=example.com
```

## Turn off HTTPS enforcement

Set the option to `false` to stop redirecting HTTP traffic to HTTPS:

```bash
juju config gateway-api-integrator enforce-https=false
```

With enforcement turned off:

- Plain HTTP traffic on port 80 is served and is **not** redirected to HTTPS.
- If no `certificates` relation is present, the HTTPS listener is not created and traffic is
  served over unencrypted HTTP only.
- If a `certificates` relation is present, both HTTP and HTTPS listeners are served, but HTTP is
  still not redirected to HTTPS.
- The `Strict-Transport-Security` (HSTS) header is no longer injected.
- The `external-hostname` configuration option becomes optional.

The charm reflects the disabled state in its status message, for example:

```{terminal}
:scroll:
juju status

App                     Version  Status  Scale  Charm                   Channel  Rev  Address         Exposed  Message
gateway-api-integrator           active      1  gateway-api-integrator  1/static xxx  10.152.183.178  no       Gateway addresses: 10.43.45.1 (enforce-https is set to false)

```

```{warning}
Turning off HTTPS enforcement lets clients reach your services over unencrypted HTTP, which
exposes traffic to interception and downgrade attacks. Only disable enforcement when plain HTTP
is acceptable for your deployment, for example when TLS is terminated by another component in
front of the gateway.
```

## Re-enable HTTPS enforcement

Set the option back to `true`:

```bash
juju config gateway-api-integrator enforce-https=true
```

Make sure a `certificates` relation is in place first; otherwise the charm blocks with
`Certificates relation is required when enforce-https is enabled.`
````

- [ ] **Step 2: Register the guide in the how-to index `toctree`**

In [docs/how-to/index.md](docs/how-to/index.md), add the new page to the `toctree` directly after the gateway-class entry.

Replace:

```markdown
```{toctree}
:maxdepth: 1
Select a gateway class <select-gateway-class.md>
Upgrade <upgrade.md>
Contribute <contribute>
```
```

with:

```markdown
```{toctree}
:maxdepth: 1
Select a gateway class <select-gateway-class.md>
Enforce HTTPS <enforce-https.md>
Upgrade <upgrade.md>
Contribute <contribute>
```
```

- [ ] **Step 3: Link the guide from the landing page**

In [docs/index.md](docs/index.md), extend the **Deployment** row of the `list-table` so the new guide appears next to the gateway-class guide.

Replace:

```markdown
* - **Deployment**
  - {ref}`Select a gateway class <how_to_select_gateway_class>`
```

with:

```markdown
* - **Deployment**
  - {ref}`Select a gateway class <how_to_select_gateway_class>` | {ref}`Enforce HTTPS <how_to_enforce_https>`
```

- [ ] **Step 4: Build the docs and verify no warnings for the new page**

Run:

```bash
cd docs && make html
```

Expected: the build finishes successfully. There must be no `WARNING` mentioning `enforce-https`, no "document isn't included in any toctree" warning for `how-to/enforce-https`, and no "undefined label: how_to_enforce_https" warning.

- [ ] **Step 5: Check links resolve**

Run:

```bash
cd docs && make linkcheck
```

Expected: linkcheck completes without reporting a `broken` link for `how-to/enforce-https`.

- [ ] **Step 6: Lint the new page against the style guide**

Run:

```bash
cd docs && make vale CHECK_PATH=how-to/enforce-https.md
```

Expected: Vale reports `0 errors`. Address any errors it reports on the new file; warnings/suggestions are informational.

- [ ] **Step 7: Commit**

```bash
git add docs/how-to/enforce-https.md docs/how-to/index.md docs/index.md
git commit -m "docs: add how-to guide for enforcing HTTPS"
```

---

## Self-Review

**1. Spec coverage:**
- "Add a how-to guide for `enforce-https`" → Task 1, Step 1 creates `docs/how-to/enforce-https.md`.
- "mentioning that it's enforced by default" → covered in the intro and the "Keep HTTPS enforced (default)" section.
- "how to turn it off" → "Turn off HTTPS enforcement" section with the exact `juju config ... enforce-https=false` command.
- "+ consequences" → the bulleted consequences list plus the security `warning` admonition.
- "published and available on RTD" → registering the page in the `toctree` (Step 2) and linking it from the landing page (Step 3) is what makes it render and publish; the build/linkcheck/vale steps verify it.
- `external-hostname` "if necessary; should be covered in the tutorial" → intentionally NOT a separate guide; its interaction with enforcement is noted inline (becomes optional when disabled; required in ingress mode when enforced) and the tutorial already covers `external-hostname`.

**2. Placeholder scan:** No `TBD`/`TODO`/"add appropriate ..." placeholders. All page content and edit blocks are complete and literal.

**3. Type/anchor consistency:** The page defines `(how_to_enforce_https)=`; both the landing-page reference in Step 3 and the "Produces" interface use the identical anchor `how_to_enforce_https`. The `toctree` entry filename `enforce-https.md` matches the created file path.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-24-enforce-https-how-to.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
