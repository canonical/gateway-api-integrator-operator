---
myst:
  html_meta:
    "description lang=en": "Learn how to expose services with static HTTP, TCP, TLS and UDP routes using the gateway-api-integrator charm"
---

(how_to_configure_extra_routes)=

# How to expose services with static routes

The `extra-routes` configuration option exposes Services in the charm's model through the
`Gateway` without a relation. Use it for workloads that don't provide an `ingress` or
`gateway-route` integration, or that need non-HTTP protocols such as MQTT over TLS or QUIC.

The `external-ips` option sets the addresses requested for the `Gateway`
(`Gateway.spec.addresses`), for gateway classes such as `envoy` that don't assign one on their
own.

## Configure routes

`extra-routes` is a JSON list. Each entry has these fields:

| Field | Applies to | Description |
| --- | --- | --- |
| `name` | all | Unique DNS label identifying the route. |
| `protocol` | all | `http` (default), `tcp`, `tls-terminate` or `udp`. |
| `service` | all | Name of a Service in the charm's model. |
| `service_port` | all | Port of the Service. |
| `hostnames` | `http`, `tls-terminate` | Hostnames served by the route. Certificates are requested for them. For `tls-terminate`, the first hostname selects the certificate. |
| `path_prefix` | `http` | Path prefix to match. Defaults to `/`. |
| `strip_prefix` | `http` | Rewrite the matched prefix to `/` before forwarding. |
| `port` | `tcp`, `tls-terminate`, `udp` | Port of the dedicated Gateway listener. Ports 80 and 443 are reserved for TCP. |

For example:

```bash
juju config gateway-api-integrator \
  gateway-class=envoy \
  external-ips=10.0.0.5 \
  extra-routes='[
    {"name": "ui", "service": "web", "service_port": 8080,
     "hostnames": ["app.example.com"]},
    {"name": "mqtts", "protocol": "tls-terminate", "port": 8883,
     "service": "emqx", "service_port": 1883, "hostnames": ["app.example.com"]},
    {"name": "mqtt-quic", "protocol": "udp", "port": 14567,
     "service": "emqx", "service_port": 14567}
  ]'
```

HTTP hostnames are served on the shared HTTP and HTTPS listeners. They follow the
`enforce-https` and `hsts-max-age` options like the hostnames of related applications, and are
published to the `dns-record` relation.

## Requirements

- The Gateway API `TCPRoute` and `UDPRoute` CRDs, served as `v1` or `v1alpha2`, when `tcp`,
  `tls-terminate` or `udp` routes are configured. The unit is blocked if they are missing.
- Services in the same namespace as the charm.
