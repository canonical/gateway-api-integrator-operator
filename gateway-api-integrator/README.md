<!-- vale Canonical.007-Headings-sentence-case = NO -->
# Gateway API integrator operator
<!-- vale Canonical.007-Headings-sentence-case = YES -->

[![CharmHub Badge](https://charmhub.io/gateway-api-integrator/badge.svg)](https://charmhub.io/gateway-api-integrator)
[![Publish to edge](https://github.com/canonical/gateway-api-integrator-operator/actions/workflows/publish_gateway_api_integrator_charm.yaml/badge.svg)](https://github.com/canonical/gateway-api-integrator-operator/actions/workflows/publish_gateway_api_integrator_charm.yaml)
[![Promote charm](https://github.com/canonical/gateway-api-integrator-operator/actions/workflows/promote_gateway_api_integrator_charm.yaml/badge.svg)](https://github.com/canonical/gateway-api-integrator-operator/actions/workflows/promote_gateway_api_integrator_charm.yaml)
[![Discourse Status](https://img.shields.io/discourse/status?server=https%3A%2F%2Fdiscourse.charmhub.io&style=flat&label=CharmHub%20Discourse)](https://discourse.charmhub.io)

A Juju charm that deploys and manages a [Gateway API integrator](https://gateway-api.sigs.k8s.io/) on Kubernetes. Gateway API is an official Kubernetes project focused on L4 and L7 routing in Kubernetes. This project represents the next generation of Kubernetes Ingress, Load Balancing, and Service Mesh APIs. From the outset, it has been designed to be generic, expressive, and role-oriented. This charm simplifies deployment and operations of Gateway API Integrator. It allows for deployment on many different Kubernetes platforms, including [Canonical K8s](https://ubuntu.com/kubernetes).

As such, the charm provides smooth operations for those looking to take control of their own Gateway API deployment, and it gives them the freedom to deploy on the Kubernetes platform of their choice.

For DevOps or SRE teams this charm will make operating a Gateway API straightforward through Juju's clean interface. It will allow deployment into multiple environments for testing of changes.

For information about how to deploy, integrate, and manage this charm, see the Official [gateway-api-integrator charm Documentation](https://canonical.com/juju/docs/gateway-api-integrator-charm/).

## Get started

To begin, refer to the [Getting Started](https://canonical.com/juju/docs/gateway-api-integrator-charm/latest/tutorial/getting-started/) tutorial for step-by-step instructions.

### Basic operations

#### Configure the gateway class

The configuration `gateway-class` sets gateway controller for the Kubernetes resource.

On [canonical-k8s](https://snapcraft.io/install/k8s/ubuntu), for example, to set it to `cilium`, run the following
command:

```
juju config gateway-api-integrator gateway-class=cilium
```

#### Integrate with a certificate provider charm

The `certificates` relation provides the gateway-api-integrator charm with TLS termination.

1. Deploy a TLS provider charm
```
juju deploy self-signed-certificates
```

2. Integrate the gateway-api-integrator charm with the TLS provider charm
```
juju integrate gateway-api-integrator self-signed-certificates
```

#### Configure HSTS

When HTTPS is enforced (`enforce-https=true`), the charm injects a
`Strict-Transport-Security` header on HTTPS routes. The `hsts-max-age`
configuration sets the `max-age` directive (in seconds) of that header. It
defaults to `31536000` (1 year) and is only applied when HTTPS is enforced.
Setting it to `0` instructs browsers to clear any cached HSTS policy.

```
juju config gateway-api-integrator hsts-max-age=63072000
```

## Learn more

- [Read more](https://canonical.com/juju/docs/gateway-api-integrator-charm/)
- [Official webpage](https://gateway-api.sigs.k8s.io/)

## Project and community

The Gateway API Integrator Operator is a member of the Ubuntu family. It's an
open source project that warmly welcomes community projects, contributions,
suggestions, fixes and constructive feedback.

- [Code of conduct](https://ubuntu.com/community/docs/ethos/code-of-conduct)
- [Get support](https://discourse.charmhub.io/)
- [Contribute](../CONTRIBUTING.md)
- [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
