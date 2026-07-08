# Gateway API Integrator Operator - Terraform Product

This terraform configuration deploys the complete Gateway API Integrator solution, including both the `gateway-api-integrator` and `ingress-configurator` charms, along with their required integrations.

## Architecture

The product consists of:
- **gateway-api-integrator**: Main charm that manages Gateway API resources
- **ingress-configurator**: Charm that bridges the `ingress` relation from workload charms to the `gateway-route` relation, allowing users to configure custom hostnames and paths.

## Prerequisites

- Terraform >= 1.6
- Juju provider for Terraform >= 1.1
- A Juju model where you want to deploy the charms

## Usage

1. Edit `main.tf` to add the module:
   ```hcl
    # Gateway API Integrator Product Module
    module "gateway" {
      source = "git::https://github.com/canonical/gateway-api-integrator-operator//terraform/product?depth=1"
      model_uuid = local.juju_model_uuid

      gateway_api_integrator = {
        channel = "1/stable"
        revision = 165
        base    = "ubuntu@24.04"
        config = {
          gateway-class = "ck-gateway"
        }
      }

      ingress_configurator = {
        channel = "latest/stable"
        revision = 95
        base    = "ubuntu@24.04"
        config = {
          hostname = "your_hostname"
          paths = "/path1,/path2"
        }
      }
    }
   ```

2. Edit `main.tf` to integrate Gateway API Integrator with tls provider charm:
   ```hcl

    resource "juju_integration" "gai_lego" {
      model_uuid = local.juju_model_uuid

      application {
        name     = module.gateway.gateway_api_integrator_app_name
        endpoint = "certificates"
      }

      application {
        name     = juju_application.lego.name
        endpoint = "certificates"
      }
    }
   ```

2. Edit `main.tf` to integrate Ingress Configurator with ingress requirer charm:
   ```hcl

    resource "juju_integration" "app_ingress" {
      model_uuid = var.model_uuid

      application {
        name     = module.gateway.ingress_configurator_app_name
        endpoint = "ingress"
      }

      application {
        name     = module.my_charm.netbox_app_name
        endpoint = "ingress"
      }
    }
   ```
4. Initialize and apply terraform:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

## Variables

### Required
- `model_uuid`: UUID of the Juju model where charms will be deployed

### Gateway API Integrator
- `gateway_api_integrator.app_name`: Application name (default: "gateway-api-integrator")
- `gateway_api_integrator.channel`: Charm channel (default: "1/stable")
- `gateway_api_integrator.config`: Application configuration map
- `gateway_api_integrator.units`: Number of units (default: 1)

### Ingress Configurator
- `ingress_configurator.app_name`: Application name (default: "ingress-configurator")
- `ingress_configurator.channel`: Charm channel (default: "latest/stable")
- `ingress_configurator.config`: Application configuration map
- `ingress_configurator.units`: Number of units (default: 1)

## Outputs

- `gateway_api_integrator_app_name`: Name of the deployed gateway-api-integrator application
- `ingress_configurator_app_name`: Name of the deployed ingress-configurator application
- `gateway_api_integrator_requires`: Required relation endpoints for gateway-api-integrator
- `gateway_api_integrator_provides`: Provided relation endpoints for gateway-api-integrator
- `ingress_configurator_requires`: Required relation endpoints for ingress-configurator
- `ingress_configurator_provides`: Provided relation endpoints for ingress-configurator

## Relations

The following integration is automatically created:
- `gateway-route` relation between `gateway-api-integrator` and `ingress-configurator`.

## Testing the deployment

The product and its modules ship
[Terraform tests](https://developer.hashicorp.com/terraform/language/tests)
(`*.tftest.hcl`) that deploy the charms into a throwaway Juju model and assert
the resulting applications. This is the recommended way to validate the
deployment end to end.

### Prerequisites

- Terraform >= 1.6
- A bootstrapped Juju controller on a Kubernetes cloud (for example
  [MicroK8s](https://microk8s.io/) or
  [Canonical K8s](https://ubuntu.com/kubernetes)), reachable through the local
  Juju client. The `juju` Terraform provider uses your active Juju CLI
  credentials, so make sure `juju status` works before running the tests.

### Run the tests

From this directory (`terraform/product`):

```bash
terraform init
terraform test
```

`terraform test`:

1. Creates a temporary Juju model named `tf-testing-<timestamp>`.
2. Deploys `gateway-api-integrator` (channel `1/stable`) and
   `ingress-configurator` (channel `latest/stable`) and integrates them over
   the `gateway-route` relation.
3. Asserts that both applications are deployed with the expected names.
4. Destroys the temporary model once the run completes.

Each module can also be tested in isolation, for example:

```bash
cd ../modules/gateway-api-integrator
terraform init
terraform test
```

### Validate without deploying

To lint and validate the configuration without contacting a Juju controller:

```bash
terraform init
terraform fmt -check -recursive
terraform validate
```
