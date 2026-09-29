(explanation_charm_design)=

# Charm design

At its core, the `gateway-api-integrator` charm deploys and manages a `Gateway` Kubernetes resource, configuring the cluster's gateway controller(s) to route traffic to backend applications. In general, it has been designed to be generic, expressive, and role-oriented.

## TLS termination

By default, TLS termination is enabled on the `gateway-api-integrator` charm, which means that a TLS provider charm ( like `self-signed-certificates` or `lego` ) is needed to provide a certificate to the `gateway-api-integrator` charm. We recommend enabling TLS for most of the cases as it provides better security and is considered a best practice in general.

## Ingress-configurator

In most cases, we recommend pairing the `gateway-api-integrator` charm with the [`ingress-configurator` charm](https://charmhub.io/ingress-configurator), which gives you the most features and flexibility. See the section on {ref}`how to manage multiple workloads <how_to_route_multiple_workloads>` to learn more on how to deploy and configure the `ingress-configurator` charm.

While it is possible to provide ingress to your application using only the `gateway-api-integrator` charm, it's usually not recommended since it has a few restrictions:

1. You are limited to one relation per `gateway-api-integrator` charm.
2. You are required to expose your application under a path prefix ( e.g., `https://example.com/<juju-model-name>-<juju-application-name>`)

Therefore, we only recommend using only the `gateway-api-integrator` charm if you have a very basic requirement and can accommodate the restrictions mentioned above.