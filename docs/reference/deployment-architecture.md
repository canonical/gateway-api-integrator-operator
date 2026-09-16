---
myst:
  html_meta:
    "description lang=en": "High-level deployment architecture for gateway-api-integrator and ingress-configurator"
---

(reference_deployment_architecture)=

# Deployment architecture

The intended deployment uses one `gateway-api-integrator` application to manage a
shared Kubernetes `Gateway`. Backend applications connect to the Gateway through
`ingress-configurator`, which translates the standard `ingress` interface into
Gateway API routes.

Deploy one `ingress-configurator` application for each backend or route. Each instance
integrates with its backend over the `ingress` interface and with
`gateway-api-integrator` over the `gateway-route` interface.

## Deployment diagram

```{mermaid}
%%{init: {'flowchart': {'subGraphTitleMargin': {'top': -22, 'bottom': 0}}}}%%
flowchart LR
    client["Client"]

    subgraph cluster["Kubernetes cluster"]
        controller["Gateway API controller"]

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
    end

    tls -. "certificates" .-> gai
    app_a <-. "ingress" .-> ic_a
    app_b <-. "ingress" .-> ic_b
    ic_a <-. "gateway-route" .-> gai
    ic_b <-. "gateway-route" .-> gai

    gai --> gateway
    ic_a --> route_a
    ic_b --> route_b
    controller --> gateway

    client --> gateway
    gateway --> route_a --> service_a --> app_a
    gateway --> route_b --> service_b --> app_b

    style cluster stroke-width:3px
```

## Component responsibilities

`gateway-api-integrator`
: Creates and manages the shared `Gateway` and TLS `Secret`. It obtains certificates
through the `certificates` integration and publishes Gateway information to every
related `ingress-configurator`.

`ingress-configurator`
: Receives backend information through the `ingress` integration and creates the
`HTTPRoute` resources that attach the backend to the shared Gateway. If required,
it also creates a Kubernetes `Service` for the backend.

Gateway API controller
: Watches the Gateway API resources and configures the cluster's ingress data plane
and load-balancer address.

Backend application
: Provides its address and port through the `ingress` integration. Each backend or
independently configured route uses a dedicated `ingress-configurator` application.

## Integration layout

The deployment uses these integrations:

| Provider                 | Requirer                 | Integration endpoint | Purpose                                              |
| ------------------------ | ------------------------ | -------------------- | ---------------------------------------------------- |
| TLS certificate provider | `gateway-api-integrator` | `certificates`       | Issues certificates for HTTPS listeners              |
| `gateway-api-integrator` | `ingress-configurator`   | `gateway-route`      | Shares Gateway details and HTTPS mode                |
| `ingress-configurator`   | Backend application      | `ingress`            | Exchanges backend details and the public ingress URL |

The certificates integration is required while HTTPS enforcement is enabled, which is
the default.

For the implementation details inside `gateway-api-integrator`, see
{ref}`reference_charm_architecture`. For deployment instructions, see
{ref}`tutorial_using_gateway_route`.
