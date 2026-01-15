<!-- vale Canonical.007-Headings-sentence-case = NO -->
# Gateway Route Configurator operator
<!-- vale Canonical.007-Headings-sentence-case = YES -->

[![CharmHub Badge](https://charmhub.io/gateway-route-configurator/badge.svg)](https://charmhub.io/gateway-route-configurator)
[![Publish to edge](https://github.com/canonical/gateway-api-integrator-operator/actions/workflows/publish_gateway_route_configurator_charm.yaml/badge.svg)](https://github.com/canonical/gateway-api-integrator-operator/actions/workflows/publish_gateway_route_configurator_charm.yaml)
[![Promote charm](https://github.com/canonical/gateway-api-integrator-operator/actions/workflows/promote_gateway_route_configurator_charm.yaml/badge.svg)](https://github.com/canonical/gateway-api-integrator-operator/actions/workflows/promote_gateway_route_configurator_charm.yaml)
[![Discourse Status](https://img.shields.io/discourse/status?server=https%3A%2F%2Fdiscourse.charmhub.io&style=flat&label=CharmHub%20Discourse)](https://discourse.charmhub.io)

A Juju charm that deploys in between a [Gateway API integator](https://gateway-api.sigs.k8s.io/) and an ingress requirer charm.

For information about how to deploy, integrate, and manage this charm, see the Official [gateway-route-configurator charm Documentation](https://charmhub.io/gateway-route-configurator/docs).

## Get started

To begin, refer to the [Getting Started](https://charmhub.io/gateway-route-configurator/docs/tutorial-getting-started) tutorial for step-by-step instructions.

## Usage

Deploy the charm:

```bash
juju deploy gateway-route-configurator --channel=latest/edge --config hostname=example.com paths=/app1,/app2
```

Integrate with the Gateway API Integrator charm:

```bash
juju relate gateway-api-integrator:gateway-route gateway-route-configurator
```

Integrate with ingress requirer
```bash
juju relate gateway-route-configurator:ingress flask-k8s
```
