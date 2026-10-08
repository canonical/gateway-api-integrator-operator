---
myst:
  html_meta:
    "description lang=en": "How-to guides for Gateway API integrator charm"
---

(how_to_index)=

# How-to guides

Manage the full operations lifecycle of the Gateway API integrator charm, from binding a
`GatewayClass` and publishing routes through TLS hardening and ongoing maintenance.
Each guide assumes that you have already deployed the charm with Juju.

## Traffic routing and endpoints

The charm programs `Gateway` and `HTTPRoute` resources to expose workloads through a gateway
controller. These guides cover selecting the controller to bind to, controlling the hostname
clients use, sharing one Gateway across several backends, and inspecting the URLs that result.

* {ref}`Select a gateway class <how_to_select_gateway_class>`: Bind the `Gateway` resource to a `GatewayClass` supplied by a controller installed on the cluster.
* {ref}`Configure the external hostname <how_to_configure_external_hostname>`: Set the FQDN served through the `ingress` relation and used for the listener, certificate, published URL, and DNS records.
* {ref}`Route traffic to multiple workloads <how_to_route_multiple_workloads>`: Share a single Gateway across several backends by deploying one `ingress-configurator` application per route.
* {ref}`Get proxied endpoints <how_to_get_proxied_endpoints>`: Run the `get-proxied-endpoints` action to retrieve the gateway and application URLs.

## TLS and transport security

The charm enforces HTTPS by default, so it requires a certificate provider and redirects plain
HTTP to HTTPS. These guides cover supplying certificates, adjusting HTTPS enforcement, and tuning
the policy that browsers apply after reaching the hostname over HTTPS.

* {ref}`Provide a certificate <how_to_provide_a_certificate>`: Integrate a TLS provider such as `self-signed-certificates`, `manual-tls-certificates`, or LEGO to satisfy the `certificates` relation.
* {ref}`Configure HTTPS enforcement <how_to_enforce_https>`: Keep or turn off the default HTTP-to-HTTPS redirect, and control whether an HTTPS listener is created.
* {ref}`Configure HSTS <how_to_configure_hsts>`: Set the `Strict-Transport-Security` `max-age` that browsers apply to the hostname.

## Maintenance and development

Upgrades and community contributions ensure the Gateway API integrator charm stays current
and benefits from ongoing improvements.

* {ref}`Upgrade <how_to_upgrade>`: Refresh the charm to a newer revision or channel with `juju refresh`.
* {ref}`Contribute <how_to_contribute>`: Set up a development and documentation workflow to build the charm, run tests, and submit improvements.

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
