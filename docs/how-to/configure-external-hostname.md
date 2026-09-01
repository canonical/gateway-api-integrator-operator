---
myst:
  html_meta:
    "description lang=en": "Learn how to configure the external hostname for the gateway-api-integrator charm"
---

(how_to_configure_external_hostname)=

# How to configure the external hostname

The `external-hostname` configuration option sets the fully qualified domain name (FQDN) that the
`gateway-api-integrator` charm serves when applications are routed through the direct `ingress`
relation. The charm uses this hostname for the `Gateway` listener, the requested TLS certificate,
the published ingress URL, and any DNS records it manages. It is a string option with no default.

```{important}
`external-hostname` applies only to the direct `ingress` relation. When routing through the
`gateway-route` relation (for example with the `ingress-configurator` charm), hostnames come from
the relation data, and setting `external-hostname` leaves the charm in a blocked state. Leave it
unset in that case. See {ref}`tutorial_using_gateway_route`.
```

## Set the external hostname

Set the option to the FQDN that clients use to reach your service:

```bash
juju config gateway-api-integrator external-hostname=<fqdn>
```

For example:

```bash
juju config gateway-api-integrator external-hostname=ingress.example.com
```

The value must be a valid FQDN; an invalid value leaves the charm in a blocked state until it is
corrected.

```{note}
When the charm is related to a TLS certificates provider — which is required while HTTPS is
enforced, the default — `external-hostname` must be set for the `ingress` relation. Without it,
the charm stays in a blocked state. See {ref}`how_to_enforce_https`.
```

## Unset the external hostname

Remove the option to clear the configured hostname:

```bash
juju config gateway-api-integrator --reset external-hostname
```

Unset it when you switch to routing through the `gateway-route` relation, or when serving plain
HTTP through the `ingress` relation without TLS and without a fixed hostname.
