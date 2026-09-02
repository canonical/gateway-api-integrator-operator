---
myst:
  html_meta:
    "description lang=en": "Learn how to configure the external hostname for the gateway-api-integrator charm"
---

(how_to_configure_external_hostname)=

# How to configure the external hostname

```{note}
`external-hostname` applies only to the `ingress` relation.
When routing through the `gateway-route` relation (with the `ingress-configurator` charm),
hostnames come from the relation data, and setting `external-hostname` leaves the charm in a blocked state.
Leave it unset in that case.
See {ref}`tutorial_using_gateway_route`.
```

The `external-hostname` configuration option sets the fully qualified domain name (FQDN) that the
`gateway-api-integrator` charm serves when backend applications are routed through the `ingress`
relation directly.
The charm uses this hostname for the `Gateway` listener, the requested TLS certificate,
the published ingress URL, and any DNS records it manages.
It is a string option with no default.

On the `ingress` relation, `external-hostname` is required whenever a `certificates` relation is
present. It is optional only when HTTPS enforcement is disabled (see {ref}`how_to_enforce_https`)
and there is no `certificates` relation. In that case you can still set it to serve plain HTTP on
that hostname, or leave it unset to serve plain HTTP on the gateway's load-balancer IP address.
When it is unset, clients reach the gateway through that IP address instead of a hostname, and the
published ingress URL becomes `http://<gateway-address>`.

## Set the external hostname

Set the option to the FQDN that clients use to reach your service:

```bash
juju config gateway-api-integrator external-hostname=<fqdn>
```

For example:

```bash
juju config gateway-api-integrator external-hostname=ingress.example.com
```

The value must be a valid FQDN;
an invalid value leaves the charm in a blocked state until it is corrected.

## Unset the external hostname

Remove the option to clear the configured hostname:

```bash
juju config gateway-api-integrator --reset external-hostname
```

You must unset it when you switch to routing through the `gateway-route` relation.
On the `ingress` relation you can also unset it to serve plain HTTP on the gateway's IP
address instead of a hostname, as described above.
