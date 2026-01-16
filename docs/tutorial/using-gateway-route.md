<!-- vale Canonical.007-Headings-sentence-case = NO -->
# Deploy the Gateway API integrator and Gateway Route Configurator charms
<!-- vale Canonical.007-Headings-sentence-case = YES -->

## What you'll do
This tutorial will walk you through deploying the gateway-api-integrator and gateway-route-configurator charms; you will:
- Deploy and configure the gateway-api-integrator charm
- Establish an integration with a TLS provider charm
- Deploy and configure the gateway-route-configurator charm
4- Deploy a ingress requirer charm and provide gateway

## Prerequisites
- A Kubernetes cluster with a gateway controller installed.
- A host machine with Juju version 3.3 or above.

## Deploy and configure the gateway-api-integrator charm
- Deploy and configure the charm
```
juju deploy gateway-api-integrator
juju config gateway-api-integrator gateway-class=cilium
```

## Establish an integration with a TLS provider charm
- Deploy a TLS provider
```
juju deploy self-signed-certificates
```

- Integrate the gateway-api-integrator charm with the TLS provider 
```
juju integrate gateway-api-integrator self-signed-certificates
```

## Deploy and configure the gateway-route-configurator charm
- Deploy and configure the charm
```
juju deploy gateway-route-configurator
juju config gateway-route-configurator hostname=testing.com paths=/app1,/app2
```

- Integrate with the gateway-api-integrator charm
```
juju integrate gateway-api-integrator:gateway-route gateway-route-configurator:gateway-route
```

## Deploy and integrate the flask-k8s charn
- Deploy and integrate the charm
```
juju deploy flask-k8s
juju integrate flask-k8s:ingress gateway-route-configurator:ingress
```

Check `juju status` to verify that the deployment was successful. The terminal output should look similar to the following:
```
App                         Version  Status  Scale  Charm                       Channel      Rev  Address         Exposed  Message
flask-k8s                            active      1  flask-k8s                   latest/edge   19  10.152.183.114  no                                                                          
gateway-api-integrator               active      1  gateway-api-integrator                     0  10.152.183.106  no       Gateway addresses: 10.43.45.1                                      
gateway-route-configurator           active      1  gateway-route-configurator                 0  10.152.183.37   no       Ready                                                              
self-signed-certificates             active      1  self-signed-certificates    1/stable     317  10.152.183.236  no                                                                          
                                                                                                                     
Unit                           Workload  Agent  Address     Ports  Message                                                          
flask-k8s/0*                   active    idle   10.1.0.123                                                                             
gateway-api-integrator/0*      active    idle   10.1.0.81          Gateway addresses: 10.43.45.1                                                
gateway-route-configurator/0*  active    idle   10.1.0.202         Ready                                                                    
self-signed-certificates/0*    active    idle   10.1.0.187                                                                                         
                                                                                                              
Integration provider                   Requirer                                  Interface         Type     Message
flask-k8s:secret-storage               flask-k8s:secret-storage                  secret-storage    peer       
gateway-api-integrator:gateway-route   gateway-route-configurator:gateway-route  gateway-route     regular    
gateway-route-configurator:ingress     flask-k8s:ingress                         ingress           regular
self-signed-certificates:certificates  gateway-api-integrator:certificates       tls-certificates  regular

```

Now curl the endpoint:
```
$ curl -k --resolve testing.com:443:10.43.45.1 https://testing.com/app1      
```
