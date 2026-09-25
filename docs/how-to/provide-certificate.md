---
myst:
  html_meta:
    "description lang=en": "Learn how to provide a TLS certificate to the gateway-api-integrator charm"
---

(how_to_provide_a_certificate)=

# How to provide a certificate

The `gateway-api-integrator` charm enforces HTTPS by default.
To deploy the charm successfully with the default `enforce-https=true` configuration,
you must integrate it with a certificate provider through the `certificates` relation.

Without this integration, the charm enters a blocked state:

```{terminal}
:output-only:
gateway-api-integrator/0  blocked  idle  Certificates relation is required when enforce-https is enabled.
```

If you intentionally need to serve unencrypted HTTP instead, you can disable HTTPS enforcement.
See {ref}`how_to_enforce_https` for the security implications and configuration instructions.

## Prerequisites

Before you begin:

- Deploy `gateway-api-integrator` and set up either a direct `ingress` integration or
  a `gateway-route` integration. See {ref}`tutorial_getting_started` and
  {ref}`ingress-configurator-charm:tutorial_getting_started`.
- Note the hostname used when setting up the relation:
  - For a direct `ingress` relation, use the `external-hostname` configured on
    `gateway-api-integrator`.
  - For a `gateway-route` relation, use the `hostname` configured on the relevant
    `ingress-configurator` application.

## Use the self-signed-certificates charm

For development, testing, and other non-production environments, use the
[self-signed-certificates charm](https://charmhub.io/self-signed-certificates).
This is the recommended and simplest way to satisfy the certificate requirement.
The charm creates its own certificate authority (CA), issues the requested certificates,
and renews them automatically.

Deploy the certificate provider:

```bash
juju deploy self-signed-certificates
```

Integrate it with `gateway-api-integrator`:

```bash
juju integrate self-signed-certificates:certificates gateway-api-integrator:certificates
```

When the certificate is available, both applications report an active status:

```{terminal}
:scroll:
juju status

App                       Status  Scale  Charm
gateway-api-integrator    active      1  gateway-api-integrator
self-signed-certificates  active      1  self-signed-certificates

Unit                         Workload  Agent  Message
gateway-api-integrator/0*    active    idle   Gateway addresses: <gateway-address>
self-signed-certificates/0*  active    idle
```

Retrieve the certificate issued for the gateway hostname or IP address:

```bash
juju run gateway-api-integrator/leader get-certificate \
  hostname=<hostname-or-gateway-address> \
  --format=json \
  | jq -r 'to_entries[0].value.results.certificate' \
  > gateway.crt
```

```{caution}
Clients do not trust self-signed certificates by default.
Install the CA certificate on clients that must validate the gateway certificate,
or use a publicly trusted certificate provider for production.
```

## Use a certificate signed by your own CA

Use the [manual-tls-certificates charm](https://charmhub.io/manual-tls-certificates)
when you already have a CA and need to control the certificate-signing process.
This option requires you to retrieve and sign each certificate signing request (CSR),
then return the signed certificate and CA chain manually.

Follow the
[Manual TLS Certificates getting-started guide](https://charmhub.io/manual-tls-certificates/docs/h-getting-started)
for the certificate-signing workflow. For this deployment, deploy the compatible
channel and integrate it with `gateway-api-integrator`:

```bash
juju deploy manual-tls-certificates --channel=1/stable
juju integrate manual-tls-certificates:certificates gateway-api-integrator:certificates
```

After the relation creates a certificate request, follow the linked guide
to retrieve the CSR and sign the certificate. The
`manual-tls-certificates` charm then provides the certificate to
`gateway-api-integrator` through the `certificates` relation.

## Use the LEGO charm for production deployments

For production deployments with publicly resolvable domain names, use the
[LEGO charm](https://charmhub.io/lego).
The LEGO charm obtains publicly trusted certificates from an ACME-compatible server,
such as Let's Encrypt, by using the DNS-01 challenge. It also renews certificates
automatically.

Follow the [LEGO charm documentation](https://charmhub.io/lego/docs) to deploy the charm
and configure your DNS provider. Then integrate it with `gateway-api-integrator`:

```bash
juju integrate lego:certificates gateway-api-integrator:certificates
```

After the provider issues all requested certificates, `gateway-api-integrator` becomes active
and serves HTTPS traffic.
