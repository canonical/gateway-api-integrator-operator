# How to upgrade
Because the `gateway-api-integrator` charm does not manage any workload, upgrading the charm can be done directly with the `juju refresh` command:
```bash
juju refresh <gateway-api-integrator> --channel=<channel>
```