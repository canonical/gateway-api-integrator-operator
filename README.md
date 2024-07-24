[![CharmHub Badge](https://charmhub.io/gateway-api-integrator/badge.svg)](https://charmhub.io/gateway-api-integrator)
[![Publish to edge](https://github.com/canonical/gateway-api-integrator-operator/actions/workflows/publish_charm.yaml/badge.svg)](https://github.com/canonical/gateway-api-integrator-operator/actions/workflows/publish_charm.yaml)
[![Promote charm](https://github.com/canonical/gateway-api-integrator-operator/actions/workflows/promote_charm.yaml/badge.svg)](https://github.com/canonical/gateway-api-integrator-operator/actions/workflows/promote_charm.yaml)
[![Discourse Status](https://img.shields.io/discourse/status?server=https%3A%2F%2Fdiscourse.charmhub.io&style=flat&label=CharmHub%20Discourse)](https://discourse.charmhub.io)

A Juju charm that deploys and manages a [Gateway API integator](https://gateway-api.sigs.k8s.io/) on Kubernetes.
Gateway API is an official Kubernetes project focused on L4 and L7 routing in Kubernetes. This
project represents the next generation of Kubernetes Ingress, Load Balancing,
and Service Mesh APIs. From the outset, it has been designed to be generic,
expressive, and role-oriented.

This charm simplifies initial deployment and "day N" operations of Gateway API
Integrator. It allows for deployment on many different Kubernetes platforms,
including [Canonical K8s](https://ubuntu.com/kubernetes).

As such, the charm makes it easy for those looking to take control of their
own Gateway API deployment while keeping operations simple, and gives them the
freedom to deploy on the Kubernetes platform of their choice.

For DevOps or SRE teams this charm will make operating a Gateway API simple and
straightforward through Juju's clean interface. It will allow easy deployment
into multiple environments for testing of changes.

## Project and community

The Gateway API Integrator Operator is a member of the Ubuntu family. It's an
open source project that warmly welcomes community projects, contributions,
suggestions, fixes and constructive feedback.
* [Code of conduct](https://ubuntu.com/community/code-of-conduct)
* [Get support](https://discourse.charmhub.io/)
* [Contribute](https://charmhub.io/gateway-api-integrator#contributing-to-this-documentation)

Thinking about using Gateway API integrator for your next project? [Get in touch](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)!

---
For further details, [see the charm's detailed documentation](https://charmhub.io/gateway-api-integrator/docs).
