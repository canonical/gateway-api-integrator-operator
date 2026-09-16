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

```{note}
The hostname used for the certificate depends on the routing mode.
See {ref}`how_to_configure_external_hostname` for configuration details.
For complete deployments, see {ref}`tutorial_getting_started` for direct `ingress` mode
or {ref}`tutorial_using_gateway_route` for `gateway-route` mode.
```

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

Inspect the certificate subject, issuer, and Subject Alternative Names:

```bash
openssl x509 \
  -in gateway.crt \
  -noout \
  -subject \
  -issuer \
  -ext subjectAltName
```

Confirm that the certificate covers the hostname or IP address used to reach the gateway
and that its issuer is the self-signed CA.

```{caution}
Because the CA is self-signed, clients do not trust these certificates by default.
Install the CA certificate on clients that must validate the gateway certificate,
or use a publicly trusted certificate provider for production.
```

## Use a certificate signed by your own CA

Use the [manual-tls-certificates charm](https://charmhub.io/manual-tls-certificates)
when you already have a CA and need to control the certificate-signing process.
This option requires you to retrieve and sign each certificate signing request (CSR),
then return the signed certificate and CA chain manually.

The following example creates a local CA for demonstration purposes.
For an existing CA, use its certificate and private key instead.

Create a directory for the certificate files:

```bash
mkdir -p certs
```

Create the CA private key and certificate:

```bash
openssl genrsa -out certs/ca.key 4096
openssl req -new -x509 \
  -key certs/ca.key \
  -out certs/ca.crt \
  -days 3650 \
  -subj "/C=US/O=Example/CN=Example Gateway CA"
```

```{warning}
Protect `certs/ca.key`. Anyone with access to this private key can issue certificates
trusted by this CA. Do not use the demonstration CA for production deployments.
```

Deploy and integrate `manual-tls-certificates`:

```bash
juju deploy manual-tls-certificates --channel=1/stable
juju integrate manual-tls-certificates:certificates gateway-api-integrator:certificates
```

Wait for `gateway-api-integrator` to submit its certificate request:

```bash
juju run manual-tls-certificates/leader get-outstanding-certificate-requests
```

The output contains a JSON list in the `result` field. Save this list to a file:

```bash
juju run manual-tls-certificates/leader get-outstanding-certificate-requests \
  --format=json \
  | jq -r 'to_entries[0].value.results.result' \
  > certs/requests.json
```

Extract the first CSR and its relation ID:

```bash
jq -r '.[0].csr' certs/requests.json > certs/gateway.csr
RELATION_ID=$(jq -r '.[0].relation_id' certs/requests.json)
```

Inspect the CSR before signing it:

```bash
openssl req -in certs/gateway.csr -noout -text
```

Confirm that its subject and Subject Alternative Names match the addresses through which
clients reach the gateway. Sign the CSR while preserving its requested extensions:

```bash
openssl x509 -req \
  -in certs/gateway.csr \
  -CA certs/ca.crt \
  -CAkey certs/ca.key \
  -CAcreateserial \
  -out certs/gateway.crt \
  -days 365 \
  -sha256 \
  -copy_extensions copyall
```

Verify that the new certificate was signed by the CA:

```bash
openssl verify -CAfile certs/ca.crt certs/gateway.crt
```

Provide the signed certificate, CA certificate, and original CSR to the
`manual-tls-certificates` charm. The charm then provides the certificate to
`gateway-api-integrator` through the `certificates` integration:

```bash
juju run manual-tls-certificates/leader provide-certificate \
  relation-id="$RELATION_ID" \
  certificate="$(base64 -w0 certs/gateway.crt)" \
  ca-certificate="$(base64 -w0 certs/ca.crt)" \
  certificate-signing-request="$(base64 -w0 certs/gateway.csr)"
```

When the certificate is available, both applications report an active status:

```{terminal}
:scroll:
juju status

App                      Status  Scale  Charm
gateway-api-integrator   active      1  gateway-api-integrator
manual-tls-certificates  active      1  manual-tls-certificates

Unit                        Workload  Agent  Message
gateway-api-integrator/0*   active    idle   Gateway addresses: <gateway-address>
manual-tls-certificates/0*  active    idle   No outstanding requests.
```

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

If you intentionally need to serve unencrypted HTTP instead, you can disable HTTPS enforcement.
See {ref}`how_to_enforce_https` for the security implications and configuration instructions.
