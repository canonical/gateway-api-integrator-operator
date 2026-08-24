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
