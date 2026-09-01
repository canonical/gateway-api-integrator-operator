---
myst:
  html_meta:
    "description lang=en": "How-to guides for Gateway API integrator charm"
---

(how_to_index)=

# How-to guides

Task-oriented procedures for configuring, securing, and maintaining the `gateway-api-integrator` charm.

## Traffic and TLS configuration

<!--
Themes: gateway class selection, HTTPS enforcement, HTTP-to-HTTPS redirect, HSTS headers, transport security
Justification: shared configuration surface — how the gateway binds to a controller and how inbound traffic is routed and secured
User journey context: initial setup, configuration phase
Juju ecosystem scope: charm-specific (config options), cross-charm (certificates relation, ingress and gateway-route relations)
Strategic notes: enforce-https true vs false — competing security postures; hsts-max-age effective only when enforce-https=true; gateway-class value must match a GatewayClass present on the cluster
-->

```{toctree}
:maxdepth: 1
Select a gateway class <select-gateway-class.md>
Configure HTTPS enforcement <enforce-https.md>
Configure HSTS <configure-hsts.md>
Configure the external hostname <configure-external-hostname.md>
```

## Maintenance and development

<!--
Themes: charm upgrade, documentation contribution
Justification: single-page topics without a shared peer domain — merged into fallback
User journey context: maintenance phase, post-deployment
Juju ecosystem scope: charm-specific (juju refresh)
Fallback: weaker thematic connection; narrative can be framed by the specific guides in the section
-->

```{toctree}
:maxdepth: 1
Upgrade <upgrade.md>
Contribute <contribute>
```
