---
title: ADR-000 - Forwarded headers are owned by the gateway controller
author: Swetha Swaminathan
date: 2026-09-02
domain: architecture
---

# Forwarded headers are owned by the gateway controller

## Context

The gateway-api-integrator charm was updated to add `X-Forwarded-For` and
`X-Forwarded-Proto` headers on managed `HTTPRoute` resources.

During review of that change, we found that this behavior is not a good fit for portable Gateway API route configuration:

- `X-Forwarded-For` is a hop-by-hop chain managed by the proxy layer and should preserve trusted proxy information across multiple hops.
- Using `RequestHeaderModifier` to `set` `X-Forwarded-For` would overwrite any existing proxy chain.
- Using `RequestHeaderModifier` to `add` `X-Forwarded-For` would still not provide a trustworthy result without controller-side sanitization of untrusted client input.
- The proposed `%DOWNSTREAM_REMOTE_ADDRESS%` value is Envoy-specific and not a portable Gateway API mechanism and there is no other gateway API
specific environment variable.
- Forwarded header handling is typically already implemented by the underlying gateway controller or proxy, and should remain the responsbility
of the underlying controller.
- With `X-Forwarded-Proto`, while most of the time setting it manually shouldn't be problem, there might be some edge cases where manually setting its value can cause issues. For example, in the rare scenario that a load balancer is placed in front of the gateway API charm and takes care of the TLS termination by itself, then the resulting value `X-Forwarded-Proto` will be `https` whereas the HTTPRoute resource will forcefully change it to `http` since it receives a TLS terminated request.

Relevant discussion:

- PR review discussion:
  <https://github.com/canonical/gateway-api-integrator-operator/pull/344#discussion_r3902379262>

## Decision

The gateway-api-integrator charm will not explicitly manage `X-Forwarded-For` or `X-Forwarded-Proto` through `HTTPRoute` filters.

Instead, the charm will rely on the underlying gateway controller
implementation to populate and sanitize forwarded headers according to its own proxy behavior and trust model.

## Consequences

- So far the only supported gateway controller is cilium, and cilium automatically adds these headers. If a new gateway controller is added in the future, it needs to be evaluated to see if it adds these headers automatically.
