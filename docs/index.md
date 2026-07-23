---
myst:
  html_meta:
    "description lang=en": "A Juju charm for managing external access to HTTP/HTTPS in a Kubernetes cluster."
---

# Gateway API integrator operator

A Juju charm that deploys and manages [Gateway API](https://gateway-api.sigs.k8s.io/) resources (`Gateway` and `HTTPRoute`) to provide ingress for applications. The charm supports both the `gateway-route` interface and the `ingress` interface, with TLS termination handled through the `tls-certificates` relation and DNS record management through the `dns-record` relation.

This operator is built for the **Kubernetes** substrate.

## In this documentation

```{list-table}
   :header-rows: 1
   :widths: 15 30

* -
  -
* - **Get started**
  - {ref}`tutorial_getting_started` | {ref}`tutorial_using_gateway_route`
* - **Integrations**
  - {ref}`Charm architecture <reference_charm_architecture>` | {ref}`Actions <reference_actions>`
* - **Security**
  - {ref}`Overview <explanation_security_overview>`
```

## How this documentation is organized

This documentation uses the [Diátaxis documentation structure](https://diataxis.fr/).

* The {ref}`Tutorial <tutorial_index>` takes you step-by-step through a basic deployment of the Gateway API integrator charm, and through combining it with the `gateway-route` interface.
* The {ref}`How-to guides <how_to_index>` cover practical tasks such as upgrading the charm and contributing to this documentation.
* {ref}`Reference <reference_index>` provides technical details on the charm's architecture and supported actions.
* {ref}`Explanation <explanation_index>` covers the charm's workflow and security posture in more depth.

## Project and community

Gateway API is an open-source project that welcomes community contributions, suggestions, fixes and constructive feedback.

* [Read our Code of Conduct](https://ubuntu.com/community/docs/ethos/code-of-conduct)
* [Join the Discourse forum](https://discourse.charmhub.io/tag/gateway-api)
* [Discuss on the Matrix chat service](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
* Contribute and report bugs to [the Gateway API integrator operator](https://github.com/canonical/gateway-api-integrator-operator)
* Check the [release notes](https://github.com/canonical/gateway-api-integrator-operator/releases)

## Contributing to this documentation

Documentation is an important part of this project, and we take the same open-source approach to the documentation as the code. As such, we welcome community contributions, suggestions and constructive feedback on our documentation. Our documentation is hosted on the [Charmhub forum](https://discourse.charmhub.io/) to enable easy collaboration. Please use the “Help us improve this documentation” links on each documentation page to either directly change something you see that’s wrong, or ask a question, or make a suggestion about a potential change using the comments section.

If there’s a particular area of documentation that you’d like to see that’s missing, please [file a bug](https://github.com/canonical/gateway-api-integrator-operator/issues).

```{toctree}
:hidden:
Tutorial <tutorial/index.md>
Reference <reference/index.md>
How-to <how-to/index.md>
Explanation <explanation/index.md>
Changelog <../changelog.md>
```
