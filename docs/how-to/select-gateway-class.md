---
myst:
  html_meta:
    "description lang=en": "Learn how to set the gateway-class configuration for the gateway-api-integrator charm"
---

(how_to_select_gateway_class)=

# How to select a gateway class

The `gateway-class` configuration option tells the `gateway-api-integrator` charm which
[GatewayClass](https://gateway-api.sigs.k8s.io/reference/api-types/gatewayclass/)
to use when creating the `Gateway` resource.
A `GatewayClass` is associated with a gateway controller (for example "Cilium")
running on the Kubernetes cluster, so the value you choose must match a class that already exists on
the cluster.

```{caution}
The `gateway-api-integrator` charm is currently tested against the `cilium` and `ck-gateway`
gateway classes. Other gateway classes may work but are not verified.
```

## List the available gateway classes

The gateway classes available on a cluster are provided by the installed gateway controllers. List
them with `kubectl`:

```bash
kubectl get gatewayclasses
```

The `NAME` column shows the values you can use for the `gateway-class` configuration.

For example, [Canonical Kubernetes](https://documentation.ubuntu.com/canonical-kubernetes/latest/snap/howto/networking/default-gateway/)
ships the `ck-gateway` gateway class out of the box.

## Set the gateway class

Configure the charm with one of the available class names:

```bash
juju config gateway-api-integrator gateway-class=<gateway-class-name>
```

For example, to use the `ck-gateway` class shipped with Canonical Kubernetes, run:

```bash
juju config gateway-api-integrator gateway-class=ck-gateway
```

## Verify the gateway class

If no gateway class is configured, or the configured class does not exist on the cluster, the charm
goes into a blocked state and its status message lists the classes it can use.

Check the status
with:

```bash
juju status gateway-api-integrator
```

The blocked status message shows the valid options, for example:

```{terminal}
:output-only:
:scroll:
App                     Version  Status   Scale  Charm                   Channel   Rev  Address         Exposed  Message
gateway-api-integrator           blocked      1  gateway-api-integrator  1/stable  165  10.152.183.178  no       Gateway class must be one of: [cilium,ck-gateway]
```

Once a valid class is set, the charm reconciles and creates the `Gateway` resource using the
selected `GatewayClass`.
