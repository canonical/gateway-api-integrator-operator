---
myst:
  html_meta:
    "description lang=en": "Step-by-step guide for setting up a basic deployment of the Gateway API integrator charm using the ingress relation endpoint."
---

(tutorial_getting_started)=

# Deploy the Gateway API integrator charm

The Gateway API integrator charm manages Gateway API resources to provide ingress
for applications. The charm supports two different relation interfaces, and the
`ingress` interface offers a straightforward and standard way to configure basic
traffic routing. In this tutorial we'll deploy the charm to provide ingress to a simple
Flask backend application running on Kubernetes.

```{important}
The `ingress` interface has limitations in ingress configuration and with supporting
multiple backend applications. The charm offers another interface, `gateway-route`,
with advanced routing features and configuration options. Follow
{ref}`ingress-configurator-charm:tutorial_getting_started` to walk through a deployment
of Gateway API integrator using the `gateway-route` interface. 
```

## What you'll do

1. Deploy and configure the Gateway API integrator charm
2. Establish an integration with a TLS provider charm
3. Deploy a simple Flask application
4. Integrate Gateway API and the Flask application
5. Verify the routing in the terminal and in a browser

## What you'll need

You will need a working station, e.g., a laptop, with AMD64 architecture. Your working station
should have at least 4 CPU cores, 8 GB of RAM, and 50 GB of disk space.

````{tip}
You can use Multipass to create an isolated environment by running:
```
multipass launch 24.04 --name charm-tutorial-vm --cpus 4 --memory 8G --disk 50G
```
````

This tutorial requires the following software to be installed on your working station
(either locally or in the Multipass VM):

- Juju 3
- Canonical Kubernetes 1.32+

Use [Concierge](https://github.com/canonical/concierge) to set up Juju and Canonical Kubernetes:

```
sudo snap install --classic concierge
sudo concierge prepare -p k8s
```

This first command installs Concierge, and the second command uses Concierge to install
and configure Juju and Canonical Kubernetes.

For this tutorial, Juju must be bootstrapped to a Canonical Kubernetes controller. Concierge should
complete this step for you, and you can verify by checking for `msg="Bootstrapped Juju" provider=k8s`
in the terminal output and by running `juju controllers`.

If Concierge did not perform the bootstrap, run:

```
juju bootstrap k8s tutorial-controller
```

## Set up the Juju model

To manage resources effectively and to separate this tutorial’s workload from your
usual work, create a new model in the controller with:

```bash
juju add-model gateway-api-integrator-tutorial
```

## Deploy and configure the charm

Let's deploy the Gateway API integrator charm:

```bash
juju deploy gateway-api-integrator --trust --channel=1/stable
```

We'll use the `1/stable` channel for this tutorial as that's the actively maintained
channel for the charm. We must also use the `--trust` flag to provide Gateway API with
elevated permissions to interact with the Kubernetes environment (the charm uses these
permissions to create the [`Gateway`](https://gateway-api.sigs.k8s.io/reference/api-types/gateway/)
and [`HTTRoute`](https://gateway-api.sigs.k8s.io/reference/api-types/httproute/) resources).

Now let's set some required configurations for the charm: `gateway-class` and
`external-hostname`. The `gateway-class` configuration option tells the charm which
GatewayClass to use when creating the Gateway resource; for this tutorial, we'll use the
gateway class shipped with Canonical Kubernetes. The `external-hostname` configuration sets the
fully qualified domain name (FQDN) that the charm serves when backend applications are routed
through the `ingress` relation.

Configure the charm:

```bash
juju config gateway-api-integrator gateway-class=ck-gateway external-hostname=ingress.internal
```

Check the status of our deployment with `juju status`:

```{terminal}
:user: ubuntu
:host: charm-tutorial-vm
:scroll:
:copy:

juju status

Model                            Controller     Cloud/Region  Version  SLA          Timestamp
gateway-api-integrator-tutorial  concierge-k8s  k8s           3.6.28   unsupported  17:48:45Z

App                     Version  Status   Scale  Charm                   Channel   Rev  Address         Exposed  Message
gateway-api-integrator           blocked      1  gateway-api-integrator  1/stable  165  10.152.183.155  no       Certificates relation is needed if enforce-https is enabled.

Unit                       Workload  Agent  Address     Ports  Message
gateway-api-integrator/0*  blocked   idle   10.1.0.122         Certificates relation is needed if enforce-https is enabled.
```

By default, the charm redirects plain HTTP traffic to HTTPS, which requires a
TLS certificate to successfully complete the connection. The deployment is blocked
because the charm requires an integration with a TLS certificates provider.

## Establish an integration with a TLS provider charm

For this tutorial, we'll use the
[self-signed certificates charm](https://charmhub.io/self-signed-certificates) to create
a certificate authority (CA) and issue the requested certificates. This charm is the
simplest way to satisfy the certificate requirement, but you shouldn't use self-signed
certificates in production environments. For more details, see {ref}`how_to_provide_a_certificate`.

Let's deploy the charm and integrate it with Gateway API integrator using the `certificates` endpoint:

```bash
juju deploy self-signed-certificates
juju integrate self-signed-certificates:certificates gateway-api-integrator:certificates
```

Wait a couple of minutes for the deployment to settle, then check with `juju status --relations`:

```{terminal}
:user: ubuntu
:host: charm-tutorial-vm
:scroll:
:copy:

juju status --relations

Model                            Controller     Cloud/Region  Version  SLA          Timestamp
gateway-api-integrator-tutorial  concierge-k8s  k8s           3.6.28   unsupported  18:47:09Z

App                       Version  Status  Scale  Charm                     Channel   Rev  Address         Exposed  Message
gateway-api-integrator             active      1  gateway-api-integrator    1/stable  165  10.152.183.155  no       Gateway addresses: 10.43.45.0
self-signed-certificates           active      1  self-signed-certificates  1/stable  586  10.152.183.214  no       

Unit                         Workload  Agent  Address     Ports  Message
gateway-api-integrator/0*    active    idle   10.1.0.122         Gateway addresses: 10.43.45.0
self-signed-certificates/0*  active    idle   10.1.0.102         

Integration provider                   Requirer                             Interface         Type     Message
self-signed-certificates:certificates  gateway-api-integrator:certificates  tls-certificates  regular 
```

Both charms are active and idle now that the relation
has been established. Now we need to provide Gateway API integrator with an application.

```{seealso}
[`tls-certificates` interface - Charmhub](https://charmhub.io/integrations/tls-certificates)
```

## Deploy the Flask application

For this tutorial, we’ll use the [Flask K8s charm](https://charmhub.io/flask-k8s)
as our application. Let’s deploy it now:

```bash
juju deploy flask-k8s --channel edge
```

## Integrate Gateway API and the Flask application

We’ll provide a communication pathway between Gateway API integrator and
the Flask application by integrating them:

```bash
juju integrate gateway-api-integrator flask-k8s
```

Let’s check what’s going on with our deployment using `juju status --relations`:

```{terminal}
:user: ubuntu
:host: charm-tutorial-vm
:scroll:
:copy:

juju status --relations

Model                            Controller     Cloud/Region  Version  SLA          Timestamp
gateway-api-integrator-tutorial  concierge-k8s  k8s           3.6.28   unsupported  18:54:53Z

App                       Version  Status  Scale  Charm                     Channel      Rev  Address         Exposed  Message
flask-k8s                          active      1  flask-k8s                 latest/edge   19  10.152.183.170  no       
gateway-api-integrator             active      1  gateway-api-integrator    1/stable     165  10.152.183.155  no       Gateway addresses: 10.43.45.0
self-signed-certificates           active      1  self-signed-certificates  1/stable     586  10.152.183.214  no       

Unit                         Workload  Agent  Address     Ports  Message
flask-k8s/0*                 active    idle   10.1.0.12          
gateway-api-integrator/0*    active    idle   10.1.0.122         Gateway addresses: 10.43.45.0
self-signed-certificates/0*  active    idle   10.1.0.102         

Integration provider                   Requirer                             Interface         Type     Message
flask-k8s:secret-storage               flask-k8s:secret-storage             secret-storage    peer     
gateway-api-integrator:gateway         flask-k8s:ingress                    ingress           regular  
self-signed-certificates:certificates  gateway-api-integrator:certificates  tls-certificates  regular 
```

The key relation here is the one between Gateway API integrator and the Flask application:

```{terminal}
:output-only:

Integration provider                   Requirer                  Interface        Type
gateway-api-integrator:gateway         flask-k8s:ingress         ingress           regular
```

After we ran `juju integrate gateway-api-integrator flask-k8s`, Juju connected the two
applications together through the `ingress` relation endpoint. The Flask application can
now provide Gateway API integrator with its internal IP address and port (which is 8000 by
default). In return, Gateway API integrator can now act as a reverse proxy for the
application, automatically generating an external URL.

```{seealso}
[`ingress` relation endpoint - Charmhub](https://charmhub.io/integrations/ingress)
```

We’ll now test whether the routing works.

## Verify the routing

First, let’s verify that the Flask application serves traffic. We’ll need the IP address of the
Flask unit listed in the output of `juju status`. In the example terminal output above, the IP
address is `10.1.0.12`. We can also grab this information generically using `jq`:

```bash
FLASK_IP=$(juju status --format json | jq -r '.applications."flask-k8s".units."flask-k8s/0".address')
```

Test the deployment using cURL:

```bash
curl $FLASK_IP:8000
```

If the deployment is successful, the output should show HTML containing
`<title>Welcome to flask-k8s Charm</title>`.

Now we can check the external hostname set up by the Gateway API integrator charm to verify
that traffic is routed through it:

```bash
curl -k --resolve ingress.internal:443:10.43.45.0 \
   https://ingress.internal/gateway-api-integrator-tutorial-flask-k8s
```

The cURL command is more complex now. The command contains the following pieces:

* Since we're using a self-signed certificate, we must tell cURL not to verify
  the certificate by passing the `-k` flag.
* The hostname must resolve through DNS, so we've passed the `--resolve` flag.
* We configured the hostname earlier as `ingress.internal`, and we used the gateway
  address set up by the charm that's listed in `juju status` as `10.43.45.0`.
* The address contains the hostname (`ingress.internal`), the name of the Juju model
  (`gateway-api-integrator-tutorial`), and the name of the Flask application (`flask-k8s`).

If the routing is successful, the output should show the same HTML containing
`<title>Welcome to flask-k8s Charm</title>` like before. We have confirmed that traffic
is being routed through Gateway API integrator.

### Visit in a browser

The HTML output from cURL can be difficult to read in a terminal.
As a final step, let’s visit the Flask application in a browser.

Access the Flask application at `https://ingress.internal/gateway-api-integrator-tutorial-flask-k8s`
in your browser. Your browser may display a warning about the connection's security
because we used a self-signed certificate. You can safely ignore this warning.

You should see the message
"Congratulations! You’ve successfully deployed the flask-k8s charm."

````{note}
If you're using Multipass for this tutorial, you will need to route the IP from
Multipass. To do this, first get the IP of the Multipass VM. Outside of the VM, run:

```
multipass info charm-tutorial-vm
```

Then route:

```
sudo ip route add ingress.internal via <Multipass VM IP>
```
````

## Clean up the environment

Congratulations! You successfully deployed the Gateway API integrator charm, integrated it
with a basic Flask application, and verified that the routing works by accessing the external URL.

You can clean up your environment by following this guide:
{ref}`Tear down your deployment <juju:tear-things-down>`

## Next steps

You achieved a basic deployment of the Gateway API integrator charm using the `ingress` relation endpoint.
If you want to go farther in your deployment or learn more about the charm, check out these pages:

* Walk through a basic deployment using the `gateway-route` endpoint in {ref}`ingress-configurator-charm:tutorial_getting_started`.
* Learn more about {ref}`HTTPS enforcement <how_to_enforce_https>` and the {ref}`TLS requirement <how_to_provide_a_certificate>`.
