---
myst:
  html_meta:
    "description lang=en": "Learn how to route traffic from one Gateway to multiple workloads"
---

(how_to_route_multiple_workloads)=

# How to route traffic to multiple workloads

A direct integration with the `gateway-api-integrator` charm supports only one backend.

To route traffic to multiple backends through the same Gateway, use the
`ingress-configurator` charm. Deploy one `ingress-configurator` application for each
backend or route and integrate each instance with `gateway-api-integrator` through the
`gateway-route` endpoint.

For deployment, configuration, and integration instructions, see
[How to route traffic for multiple workloads through a single Gateway](https://canonical.com/juju/docs/ingress-configurator-charm/latest/how-to/gateway-api/route-multiple-workloads/).
