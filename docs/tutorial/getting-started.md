# Tutorial: deploy the gateway API integrator charm

This tutorial will walk you through deploying the gateway-api-integrator charm

## Prerequisites
* A kubernetes cluster with a gateway controller installed.
* A host machine with juju version 3.3 or above.

## Deploy
1. Deploy and configure the charm
```
juju deploy gateway-api-integrator
juju config gateway-api-integrator external-hostname=ingress.internal
```
2. Deploy a TLS provider
```
juju deploy self-signed-certificates
```
3. Integrate the gateway-api-integrator charm with the TLS provider 
```
juju integrate gateway-api-integrator self-signed-certificates
```