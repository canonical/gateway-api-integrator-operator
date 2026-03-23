---
myst:
  html_meta:
    "description lang=en": "A Juju charm for managing external access to HTTP/HTTPS in a Kubernetes cluster."
---

# Gateway API integrator operator

A [Juju](https://juju.is/) [charm](https://documentation.ubuntu.com/juju/3.6/reference/charm/) deploying and managing external access to HTTP/HTTPS services in a
Kubernetes cluster using a Gateway and an HTTPRoute resource. This requires the Kubernetes
cluster in question to have a [Gateway API controller](https://gateway-api.sigs.k8s.io/implementations/) already deployed into it.

## Project and community

Gateway API is an open-source project that welcomes community contributions, suggestions, fixes and constructive feedback.

* [Read our Code of Conduct](https://ubuntu.com/community/code-of-conduct)
* [Join the Discourse forum](https://discourse.charmhub.io/tag/gateway-api)
* [Discuss on the Matrix chat service](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
* Contribute and report bugs to [the Gateway API integrator operator](https://github.com/canonical/gateway-api-integrator-operator)
* Check the [release notes](https://github.com/canonical/gateway-api-integrator-operator/releases)

## Contributing to this documentation

Documentation is an important part of this project, and we take the same open-source approach to the documentation as the code. As such, we welcome community contributions, suggestions and constructive feedback on our documentation. Our documentation is hosted on the [Charmhub forum](https://discourse.charmhub.io/) to enable easy collaboration. Please use the “Help us improve this documentation” links on each documentation page to either directly change something you see that’s wrong, or ask a question, or make a suggestion about a potential change using the comments section.

If there’s a particular area of documentation that you’d like to see that’s missing, please [file a bug](https://github.com/canonical/gateway-api-integrator-operator/issues).

# In this documentation

|||
|-----------------|----------------|
| {ref}`Tutorial <tutorial_index>`</br>  Hands-on introductions to Gateway API integrator | {ref}`How-to  guides <how_to_index>`</br> Step-by-step guides covering key operations and common tasks |
| {ref}`Explanation <explanation_index>` </br>  Concepts - discussion and clarification of key topics | {ref}`Reference <reference_index>` </br>  Technical information - specifications, commands, architecture |

```{toctree}
:hidden:
Tutorial <tutorial/index.md>
Reference <reference/index.md>
How-to <how-to/index.md>
Explanation <explanation/index.md>
```
