# The charm's workflow
1. When the charm starts, it goes into a blocked state until TLS is configured, either via a config option or via an integration with a TLS provider charm.

2. Once TLS is configured, a gateway object containing a http and a https listener is created: The minimal gateway object. The charm will remain in blocked state until integration with an ingress requirer charm is established.

3. When integration with an ingress requirer has been established, a service, an endpoint slice and an HTTPRoute object is created: The service object and httproute

4. The ingress requirer is then notified on the available ingress endpoint.
