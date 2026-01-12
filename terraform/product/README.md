# Gateway API Integrator Operator - Terraform Product

This terraform configuration deploys the complete Gateway API Integrator solution, including both the `gateway-api-integrator` and `gateway-route-configurator` charms, along with their required integrations.

## Architecture

The product consists of:
- **gateway-api-integrator**: Main charm that manages Gateway API resources
- **gateway-route-configurator**: Companion charm that configures routes through the gateway-route relation

## Prerequisites

- Terraform >= 1.5
- Juju provider for Terraform >= 0.12.0
- A Juju model where you want to deploy the charms

## Usage

1. Copy the example variables file:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit `terraform.tfvars` to customize your deployment:
   ```hcl
   model_uuid = "your-juju-model-uuid-here"
   
   # Configure gateway-api-integrator
   gateway_api_integrator_config = {
     "external-hostname"     = "gateway.example.com"
     "gateway-class-name"    = "cilium"
     "gateway-name"          = "cilium-gateway"
     "gateway-namespace"     = "cilium-gateway"
   }
   
   # Optional: specify TLS certificates provider
   tls_certificates_app_name = "self-signed-certificates"
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
- `gateway_api_integrator_app_name`: Application name (default: "gateway-api-integrator")
- `gateway_api_integrator_channel`: Charm channel (default: "latest/edge")
- `gateway_api_integrator_config`: Application configuration map
- `gateway_api_integrator_units`: Number of units (default: 1)

### Gateway Route Configurator
- `gateway_route_configurator_app_name`: Application name (default: "gateway-route-configurator")
- `gateway_route_configurator_channel`: Charm channel (default: "latest/edge")
- `gateway_route_configurator_config`: Application configuration map
- `gateway_route_configurator_units`: Number of units (default: 1)

### Optional Integrations
- `tls_certificates_app_name`: Name of TLS certificates provider (e.g., "self-signed-certificates")
- `ingress_app_name`: Name of ingress provider (e.g., "traefik-k8s")

## Outputs

- `gateway_api_integrator_app_name`: Name of the deployed gateway-api-integrator application
- `gateway_route_configurator_app_name`: Name of the deployed gateway-route-configurator application
- `gateway_api_integrator_requires`: Required relation endpoints for gateway-api-integrator
- `gateway_api_integrator_provides`: Provided relation endpoints for gateway-api-integrator
- `gateway_route_configurator_requires`: Required relation endpoints for gateway-route-configurator
- `gateway_route_configurator_provides`: Provided relation endpoints for gateway-route-configurator

## Relations

The following integrations are automatically created:
- Gateway-route relation between gateway-api-integrator and gateway-route-configurator
- Optional TLS certificates relation (if `tls_certificates_app_name` is specified)
- Optional ingress relation (if `ingress_app_name` is specified)

## Examples

### Basic deployment
```hcl
model_uuid = "12345678-1234-1234-1234-123456789abc"

gateway_api_integrator_config = {
  "external-hostname"  = "api.example.com"
  "gateway-class-name" = "cilium"
}
```

### Deployment with TLS
```hcl
model_uuid = "12345678-1234-1234-1234-123456789abc"

gateway_api_integrator_config = {
  "external-hostname"  = "api.example.com"
  "gateway-class-name" = "cilium"
}

tls_certificates_app_name = "self-signed-certificates"
```