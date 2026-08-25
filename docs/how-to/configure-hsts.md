---
myst:
  html_meta:
    "description lang=en": "Learn how to configure the HSTS max-age for the gateway-api-integrator charm"
---

(how_to_configure_hsts)=

# How to configure HSTS

The `hsts-max-age` configuration option controls the `max-age` directive of the
[HTTP Strict Transport Security (HSTS)](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security)
`Strict-Transport-Security` header that the `gateway-api-integrator` charm injects on HTTPS
responses. The value is an integer number of seconds and defaults to `31536000` (one year).

The HSTS header tells browsers to contact the site over HTTPS only for the duration of `max-age`,
which helps prevent protocol downgrade and cookie hijacking attacks.

```{important}
The `Strict-Transport-Security` header is only injected when HTTPS is enforced
(`enforce-https=true`, the default). If HTTPS enforcement is turned off, the `hsts-max-age`
value has no effect. See {ref}`how_to_enforce_https`.
```

## Set the HSTS max age

Configure the option with the number of seconds browsers should remember to use HTTPS:

```bash
juju config gateway-api-integrator hsts-max-age=<seconds>
```

For example, to set a `max-age` of one year (the default):

```bash
juju config gateway-api-integrator hsts-max-age=31536000
```

The charm then injects the following header on HTTPS responses:

```{terminal}
:output-only:
Strict-Transport-Security: max-age=31536000
```

## Clear the HSTS policy

Set `hsts-max-age` to `0` to instruct browsers to clear any cached HSTS policy:

```bash
juju config gateway-api-integrator hsts-max-age=0
```

The charm still injects the header, but with a zero `max-age`:

```{terminal}
:output-only:
Strict-Transport-Security: max-age=0
```

This configuration is useful when you are migrating a hostname away from HTTPS-only and need clients to stop
enforcing HTTPS.

```{note}
`hsts-max-age` accepts only non-negative integers. A negative value is rejected and leaves the
charm in a blocked state until a valid value is provided.
```
