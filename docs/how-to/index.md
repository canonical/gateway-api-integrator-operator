---
myst:
  html_meta:
    "description lang=en": "How-to guides for Gateway API integrator charm"
---

(how_to_index)=

# How-to guides

Manage the full operations lifecycle of the Gateway API integrator charm, from configuring a `GatewayClass` and publishing routes through TLS hardening and maintenance. Each guide assumes that you have already deployed the charm with Juju.

## Traffic routing and endpoints

The charm manages `Gateway` and `HTTPRoute` resources to expose workloads through a gateway controller. These guides cover selecting the controller to bind to, configuring the hostname for backend applications, sharing one Gateway across several backends, and inspecting the public URLs for each backend.

* [Select a gateway class](select-gateway-class.md): Bind the `Gateway` resource to a `GatewayClass` supplied by a gateway controller installed on the cluster.
* [Configure the external hostname](configure-external-hostname.md): Set the FQDN served through the `ingress` relation and used for the listener, certificate, published URL, and DNS records.
* [Route traffic to multiple workloads](route-multiple-workloads.md): Share a single Gateway across several backends by deploying one `ingress-configurator` application per route.
* [Get proxied endpoints](get-proxied-endpoints.md): Run the `get-proxied-endpoints` action to retrieve the gateway and application URLs.

## TLS and transport security

The charm enforces HTTPS by default, so it requires a certificate provider and redirects plain HTTP to HTTPS. These guides cover supplying the TLS certificates via a provider charm, adjusting HTTPS enforcement, and tuning the policy that browsers apply after reaching the hostname over HTTPS.

* [Provide a certificate](provide-certificate.md): Integrate a TLS provider such as `self-signed-certificates`, `manual-tls-certificates`, or LEGO to satisfy the `certificates` relation.
* [Configure HTTPS enforcement](enforce-https.md): Keep or turn off the default HTTP-to-HTTPS redirect, and control whether an HTTPS listener is created.
* [Configure HSTS](configure-hsts.md): Set the `Strict-Transport-Security` `max-age` that browsers apply to the hostname.

## Maintenance and development

Upgrades and community contributions.

* [Upgrade](upgrade.md): Refresh the charm to a newer revision or channel with `juju refresh`.
* [Contribute](contribute.rst): Set up a development and documentation workflow to build the charm, run tests, and submit improvements.

```{toctree}
:hidden:

Select a gateway class <select-gateway-class.md>
Configure the external hostname <configure-external-hostname.md>
Route traffic to multiple workloads <route-multiple-workloads.md>
Get proxied endpoints <get-proxied-endpoints.md>
Provide a certificate <provide-certificate.md>
Configure HTTPS enforcement <enforce-https.md>
Configure HSTS <configure-hsts.md>
Upgrade <upgrade.md>
Contribute <contribute.rst>
```
