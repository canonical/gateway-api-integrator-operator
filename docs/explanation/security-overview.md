(explanation_security_overview)=

# Gateway API integrator security overview

This explanation covers several security-related topics for the Gateway API integrator charm. This charm is a {ref}`configurator charm <juju:workloadless-charm>` and, as such, is workloadless.

## Risks

As a workloadless charm, the attack surface is restricted to that of Juju's. You can find best practices for Juju itself in the {ref}`Juju security documentation <juju:juju-security>`.

## Machine-in-the-middle attack

This type of attack refers to an attacker intercepting traffic between a client and the service and impersonating the intended recipient, for example to trick a user into revealing sensitive data. As an ingress proxy, the charm routes client requests to backend services, so encrypting that traffic helps prevent interception and downgrade attacks.

### Good practices

By default, the charm enforces HTTPS by redirecting HTTP traffic to HTTPS and injecting a `Strict-Transport-Security` (HSTS) header. Provide a TLS certificate through the `certificates` integration and keep HTTPS enforcement enabled. See {ref}`how_to_enforce_https` for details on configuring this behaviour.

### Summary

- Use TLS certificates to encrypt traffic.
- Keep HTTPS enforcement enabled.
