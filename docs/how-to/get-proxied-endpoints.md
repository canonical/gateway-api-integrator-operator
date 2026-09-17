---
myst:
  html_meta:
    "description lang=en": "Learn how to get the endpoints proxied by the gateway-api-integrator charm"
---

(how_to_get_proxied_endpoints)=

# How to get proxied endpoints

The `get-proxied-endpoints` action returns the URLs exposed by the
`gateway-api-integrator` charm. The result includes the gateway endpoint and
the endpoints for applications integrated through the `ingress` relation. 
The charm `flask-k8s` is used as an example backend application for this guide.

```{note}
When routing through the `gateway-route` relation with the `ingress-configurator`
charm, run the [`get-proxied-endpoints` action](https://charmhub.io/ingress-configurator/actions#get-proxied-endpoints) on the `ingress-configurator` charm
instead.
```

Run the action on the leader unit:

```bash
juju run gateway-api-integrator/leader get-proxied-endpoints
```

The action returns the endpoints in the `proxied-endpoints` result. Use the
returned URL to send requests to the gateway and the proxied application.

When `external-hostname` is not set, the action returns URLs that use the
gateway IP address:

```{terminal}
juju run gateway-api-integrator/leader get-proxied-endpoints

proxied-endpoints: '{"gateway-api-integrator": {"url": "http://10.43.45.0"}, "flask-k8s":
  {"url": "http://10.43.45.0/testing-flask-k8s"}}'
```

Curl these URLs directly:

```bash
curl http://10.43.45.0/testing-flask-k8s
```

```{warning}
An unset `external-hostname` requires `enforce-https=false` when your backend 
application uses the direct `ingress` relation.

Only disable enforcement when plain HTTP is acceptable (for example, when TLS 
is terminated by another component in front of the gateway). See {ref}`how_to_enforce_https`.
```

When `external-hostname` is set and the charm has a `certificates` relation,
the action returns URLs that use the configured hostname:

```{terminal}
juju run gateway-api-integrator/leader get-proxied-endpoints

proxied-endpoints: '{"gateway-api-integrator": {"url": "https://testing.com"}, "flask-k8s":
  {"url": "https://testing.com/testing-flask-k8s"}}'
```

The hostname must resolve through DNS to an IP address that reaches the
gateway. For local testing, check the `Gateway addresses` value in
`juju status`, then use `--resolve` to map the hostname to that address:

```bash
curl -k --resolve testing.com:443:10.43.45.0 https://testing.com/testing-flask-k8s
```
