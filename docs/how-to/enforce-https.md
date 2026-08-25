---
myst:
  html_meta:
    "description lang=en": "Learn how to enable or disable HTTPS enforcement for the gateway-api-integrator charm"
---

(how_to_enforce_https)=

# How to configure HTTPS enforcement

The `enforce-https` configuration option controls whether the
`gateway-api-integrator` charm redirects plain HTTP traffic to HTTPS.
It is a boolean option and is **enabled by default** (`enforce-https=true`),
so HTTPS is enforced unless you explicitly turn it off.

When HTTPS is enforced, the charm:

- Requires an integration with a TLS certificates provider through the `certificates` relation.
- Serves an HTTP listener that issues a `301` redirect to HTTPS, alongside the HTTPS listener.
- Injects a `Strict-Transport-Security` (HSTS) header on HTTPS responses,
controlled by the `hsts-max-age` configuration option (see {ref}`how_to_configure_hsts`).

## Turn on HTTPS enforcement

HTTPS enforcement is the default state: `enforce-https` is `true` unless you have changed it.
If enforcement was previously turned off, set the option back to `true`:

```bash
juju config gateway-api-integrator enforce-https=true
```

Integrate the charm with a TLS certificate provider:

```bash
juju integrate gateway-api-integrator <certificate-provider-charm>
```

When backend applications use the direct `ingress` relation, you must also set the `external-hostname`
configuration option:

```bash
juju config gateway-api-integrator external-hostname=<hostname>
```

```{note}
Only set `external-hostname` when using the `ingress` relation directly.
When routing through the `gateway-route` relation (with the `ingress-configurator` charm),
hostnames come from the relation data and `external-hostname` must be left unset.
```

## Turn off HTTPS enforcement

```{warning}
Turning off HTTPS enforcement lets clients reach your services over unencrypted HTTP,
which exposes traffic to interception and downgrade attacks.

Only disable enforcement when plain HTTP is acceptable for your deployment
(for example, when TLS is terminated by another component in front of the gateway).
```

Set the option to `false` to stop redirecting HTTP traffic to HTTPS:

```bash
juju config gateway-api-integrator enforce-https=false
```

With enforcement turned off:

- HTTP traffic on port 80 is served and is **not** redirected to HTTPS.
- The `Strict-Transport-Security` (HSTS) header is no longer injected.

Whether HTTPS is still served then depends on the `certificates` relation:

- **Without a `certificates` relation:** traffic is served over unencrypted HTTP only
  (the HTTPS listener is not created), and `external-hostname` is optional for the `ingress` relation.
- **With a `certificates` relation:** both HTTP and HTTPS traffic is served,
  but HTTP is not redirected to HTTPS.

The charm reflects the disabled state in its status message, for example:

```{terminal}
:scroll:
juju status

Model  Controller     Cloud/Region  Version  SLA          Timestamp
test   concierge-k8s  k8s           3.6.27   unsupported  ...

App                     Version  Status  Scale  Charm                   Channel  Rev  Address         Exposed  Message
gateway-api-integrator           active      1  gateway-api-integrator  1/stable xxx  10.152.183.178  no       Gateway addresses: 10.76.109.0 (enforce-https is set to false)

Unit                       Workload  Agent  Address    Ports  Message
gateway-api-integrator/0*  active    idle   10.1.0.37         Gateway addresses: 10.76.109.0 (enforce-https is set to false)
```
