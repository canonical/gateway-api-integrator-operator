---
myst:
  html_meta:
    "description lang=en": "High-level deployment architecture for gateway-api-integrator and ingress-configurator"
---

(reference_deployment_architecture)=

# Deployment architecture

The recommended architecture routes multiple backend applications through a shared
Kubernetes
[`Gateway`](https://gateway-api.sigs.k8s.io/docs/concepts/api-overview/#gateway)
managed by one `gateway-api-integrator` charm. Each backend requires a separate `ingress-configurator` charm.

```{mermaid}
%%{init: {'flowchart': {'subGraphTitleMargin': {'top': -22, 'bottom': 0}}}}%%
flowchart LR

        subgraph model["Juju model"]
            tls["TLS certificate provider"]
            gai["gateway-api-integrator"]
            ic_a["ingress-configurator A"]
            ic_b["ingress-configurator B"]
            app_a["Backend application A"]
            app_b["Backend application B"]

            subgraph resources["Kubernetes resources"]
                gateway["Gateway and TLS Secret"]
                route_a["HTTPRoute A"]
                route_b["HTTPRoute B"]
                service_a["Service A"]
                service_b["Service B"]
            end
        end

    tls -. "certificates" .-> gai
    app_a <-. "ingress" .-> ic_a
    app_b <-. "ingress" .-> ic_b
    ic_a <-. "gateway-route" .-> gai
    ic_b <-. "gateway-route" .-> gai

    gai --> gateway
    ic_a --> route_a
    ic_b --> route_b

    gateway --> route_a --> service_a --> app_a
    gateway --> route_b --> service_b --> app_b
```

In the example deployment shown above, two backend applications share one Gateway
managed by `gateway-api-integrator`. Each backend has its own
`ingress-configurator` charm, which connects the backend to the shared Gateway
using
[`HTTPRoute`](https://gateway-api.sigs.k8s.io/docs/concepts/api-overview/#httproute)
resources.
The deployment contains these key components:

`gateway-api-integrator`
: Creates and manages the shared [`Gateway`](https://gateway-api.sigs.k8s.io/docs/concepts/api-overview/#gateway)
and TLS [`Secret`](https://kubernetes.io/docs/concepts/configuration/secret/). It
obtains certificates through the `certificates` relation and publishes Gateway
information to every related `ingress-configurator`.

`ingress-configurator`
: Integrates with `gateway-api-integrator` through the `gateway-route` relation to
receive details about the shared Gateway. It combines these details with backend
information from the `ingress` relation and creates an
[`HTTPRoute`](https://gateway-api.sigs.k8s.io/docs/concepts/api-overview/#httproute)
that attaches the backend to the Gateway. If required, it also creates a Kubernetes
`Service` for the backend.

Backend application
: Provides its address and port through the `ingress` relation. Each backend
uses a dedicated `ingress-configurator` charm.

```{note}
The [Kubernetes resources](https://kubernetes.io/docs/concepts/services-networking/)
in the diagram are created and managed automatically by the
`gateway-api-integrator` and `ingress-configurator` charms. Operators manage the
charms and their relations; they do not need to create these resources directly.
```

## Relations

The deployment uses these relations:

| Provider                 | Requirer                 | Relation endpoint | Purpose                                                               |
| ------------------------ | ------------------------ | -------------------- | --------------------------------------------------------------------- |
| TLS certificate provider | `gateway-api-integrator` | `certificates`       | Issues certificates for HTTPS listeners                               |
| `gateway-api-integrator` | `ingress-configurator`   | `gateway-route`      | Shares Gateway connection details and HTTP/HTTPS routing requirements |
| `ingress-configurator`   | Backend application      | `ingress`            | Exchanges backend details and the public ingress URL                  |

The `certificates` relation is required while HTTPS enforcement is enabled, which is
the default.

## Read more

- {ref}`Charm architecture <reference_charm_architecture>`
- {ref}`Deploy gateway-api-integrator with ingress-configurator <ingress-configurator-charm:tutorial_getting_started>`
- {ref}`How to route traffic for multiple workloads through a single Gateway <ingress-configurator-charm:how_to_gateway_api_route_multiple_workloads>`