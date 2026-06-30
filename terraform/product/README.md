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
        channel = "1/edge
        revision = 127
        base    = "ubuntu@24.04"
        config = {
          gateway-class = "ck-gateway"
        }
      }

      ingress_configurator = {
        channel = "latest/edge"
        revision = 2
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
3. Initialize and apply terraform:
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
- `gateway_api_integrator.channel`: Charm channel (default: "latest/edge")
- `gateway_api_integrator.config`: Application configuration map
- `gateway_api_integrator.units`: Number of units (default: 1)

### Ingress Configurator
- `ingress_configurator.app_name`: Application name (default: "ingress-configurator")
- `ingress_configurator.channel`: Charm channel (default: "latest/edge")
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
