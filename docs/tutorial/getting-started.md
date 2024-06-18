# Tutorial: Deploy the Gateway API integrator charm

## What you'll do
This tutorial will walk you through deploying the gateway-api-integrator charm, you will:
1. deploy and configure the gateway-api-integrator charm
2. Establish an itegration with a TLS provider charm

## Prerequisites
* A kubernetes cluster with a gateway controller installed.
* A host machine with juju version 3.3 or above.

## Deploy and configure the gateway-api-integrator charm
1. Deploy and configure the charm
```
juju deploy gateway-api-integrator
juju config gateway-api-integrator external-hostname=ingress.internal
```

## Establish an itegration with a TLS provider charm
1. Deploy a TLS provider
```
juju deploy self-signed-certificates
```
2. Integrate the gateway-api-integrator charm with the TLS provider 
```
juju integrate gateway-api-integrator self-signed-certificates
```