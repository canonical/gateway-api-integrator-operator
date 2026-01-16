<!-- vale Canonical.007-Headings-sentence-case = NO -->
# Gateway Route Configurator operator
<!-- vale Canonical.007-Headings-sentence-case = YES -->

[![CharmHub Badge](https://charmhub.io/gateway-route-configurator/badge.svg)](https://charmhub.io/gateway-route-configurator)
[![Publish to edge](https://github.com/canonical/gateway-api-integrator-operator/actions/workflows/publish_gateway_route_configurator_charm.yaml/badge.svg)](https://github.com/canonical/gateway-api-integrator-operator/actions/workflows/publish_gateway_route_configurator_charm.yaml)
[![Promote charm](https://github.com/canonical/gateway-api-integrator-operator/actions/workflows/promote_gateway_route_configurator_charm.yaml/badge.svg)](https://github.com/canonical/gateway-api-integrator-operator/actions/workflows/promote_gateway_route_configurator_charm.yaml)
[![Discourse Status](https://img.shields.io/discourse/status?server=https%3A%2F%2Fdiscourse.charmhub.io&style=flat&label=CharmHub%20Discourse)](https://discourse.charmhub.io)

A Juju charm that deploys in between a [Gateway API integator](https://gateway-api.sigs.k8s.io/) and an ingress requirer charm. In its current implementation the Gateway API integrator `ingress` integration doesn't allow users to specify the path their application is exposed in. The `gateway-route` relation gives full control to users for exposing their application. The Gateway Route configurator charm helps users by creating a bridge between the `ingress` and `gateway-route` integrations so users doesn't have to update their charm to use the `gateway-route` integration.

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
juju integrate gateway-api-integrator:gateway-route gateway-route-configurator
```

Integrate with the ingress requirer:
```bash
juju relate gateway-route-configurator:ingress flask-k8s
```

## Learn more

- [Read more](https://charmhub.io/gateway-api-integrator/docs)
- [Official webpage](https://gateway-api.sigs.k8s.io/)

## Project and community

The Gateway API Integrator Operator is a member of the Ubuntu family. It's an
open source project that warmly welcomes community projects, contributions,
suggestions, fixes and constructive feedback.

- [Code of conduct](https://ubuntu.com/community/code-of-conduct)
- [Get support](https://discourse.charmhub.io/)
- [Contribute](https://charmhub.io/gateway-api-integrator#contributing-to-this-documentation)
- [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)