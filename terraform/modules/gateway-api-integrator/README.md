# Terraform module for gateway-api-integrator

This is a [Terraform](https://www.terraform.io/) module that deploys the
[gateway-api-integrator](https://charmhub.io/gateway-api-integrator) charm using
the [Juju provider](https://registry.terraform.io/providers/juju/juju/latest).

The module is a Charm module as defined by CC008 (Terraform module standards): it
deploys a single charm and is intended to be consumed by higher-level component,
product, or deployment modules.

## Requirements

- Terraform `~> 1.12`
- Juju provider `>= 1.0, < 3.0`

## Usage

```hcl
module "gateway_api_integrator" {
  source     = "path/to/this/module"
  model_uuid = juju_model.this.uuid
}
```

## Inputs

| Name        | Type        | Default                  | Nullable | Description |
| ----------- | ----------- | ------------------------ | -------- | ----------- |
| app_name    | string      | "gateway-api-integrator" | no       | Name of the application in the Juju model. |
| base        | string      | null                     | yes      | The operating system on which to deploy. null lets the provider use the charm's default. |
| channel     | string      | "1/stable"               | no       | The channel to use when deploying a charm. |
| config      | map(string) | {}                       | yes      | Application config. |
| constraints | string      | null                     | yes      | Juju constraints to apply for this application. |
| model_uuid  | string      | n/a (required)           | no       | UUID of the Juju model where the application will be deployed. |
| revision    | number      | null                     | yes      | Revision number of the charm. null deploys the latest on the channel. |
| units       | number      | 1                        | yes      | Number of units to deploy. |

## Outputs

| Name        | Type   | Description |
| ----------- | ------ | ----------- |
| app_name    | string | Name of the deployed application. |
| application | object | The deployed `juju_application` resource. |
| provides    | object | Map of the provided integration endpoints. Each entry has `kind`, `name`, `endpoint`. |
| requires    | object | Map of the required integration endpoints. Each entry has `kind`, `name`, `endpoint`. |

### `provides`

| Key           | Endpoint      |
| ------------- | ------------- |
| gateway       | gateway       |
| gateway_route | gateway-route |

### `requires`

| Key          | Endpoint     |
| ------------ | ------------ |
| certificates | certificates |
| dns_record   | dns-record   |
