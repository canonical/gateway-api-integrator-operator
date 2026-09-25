---
myst:
  html_meta:
    "description lang=en": "Tutorials covering a basic deployment and usage for Gateway API integrator charm."
---

(tutorial_index)=

# Tutorials

The tutorial in this documentation set walks you through a basic deployment of the
Gateway API integrator charm using the `ingress` relation endpoint. 

```{toctree}
:maxdepth: 1
getting-started.md
```

The charm can also use the `gateway-route` endpoint to provide traffic routing for an
application, which gives you more control over the ingress configuration and the
ability to integrate with multiple ingress-requiring backends. Visit the
`ingress-configurator` charm documentation to walk through a basic deployment using
the `gateway-route` endpoint.

```{toctree}
:maxdepth: 1
Deploy Gateway API integrator and Ingress configurator <https://canonical.com/juju/docs/ingress-configurator-charm/latest/tutorial/getting-started/>
```
