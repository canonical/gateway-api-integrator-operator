# The charm's workflow
1. When the charm starts, it goes into a blocked state until TLS is configured, either via a config option or via an integration with a TLS provider charm.

2. Once TLS is configure a minimal gateway object containing a http and a https listener is created. The charm will remain in a block state until integration with an ingress requirer charm is established.
[<img src="docs/assets/windows_console.png">]

3. When integration with an ingress requirer has been established, a service, an endpoint slice and an HTTPRoute object is created.

4. The ingress requirer is then notified on the available ingress endpoint.
