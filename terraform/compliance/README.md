# CC008 Terraform compliance checker

`cc008_check.py` verifies that Terraform modules follow the CC008 (Terraform
module standards) structure and interface. HCL is parsed with `python-hcl2`.

## Run locally

```bash
uv run --group terraform python terraform/compliance/cc008_check.py \
  terraform/modules/gateway-api-integrator \
  terraform/product
```

Exit code `0` means every module passed; `1` means at least one module reported
a violation. Each violation line describes the exact gap.

## Run the unit tests

```bash
tox -e terraform-compliance
```

## Checks performed

- Required files present: `terraform.tf`, `variables.tf`, `outputs.tf`,
  `main.tf`, `README.md`.
- `terraform.tf` declares `required_version` and a `juju` provider allowing
  `>= 1.0`.
- `variables.tf` and `outputs.tf` blocks are in alphabetical order.
- Charm modules declare the mandatory variables (`app_name`, `channel`,
  `config`, `constraints`, `model_uuid`, `revision`, `units`) and outputs
  (`application`, `provides`, `requires`).
- Product (composed) modules declare the mandatory outputs (`models`,
  `metadata`).
- Remote module sources are pinned to a tag or commit (no floating branch
  references).

A module is treated as a product (composed) module when any of its files
declares a `module` block; otherwise it is treated as a charm module.

## CI

The reusable workflow `.github/workflows/terraform_cc008_check.yaml` runs this
checker; `.github/workflows/terraform_compliance.yaml` invokes it on pull
requests that touch `terraform/**`.
