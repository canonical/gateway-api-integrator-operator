# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Shared helpers for e2e tests."""

import ipaddress
from urllib.parse import urlparse

import jubilant
import requests
import urllib3
from requests.adapters import DEFAULT_POOLBLOCK, DEFAULT_POOLSIZE, DEFAULT_RETRIES, HTTPAdapter
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_fixed
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings when using verify=False
urllib3.disable_warnings(InsecureRequestWarning)


class DNSResolverAdapter(HTTPAdapter):
    """A simple mounted DNS resolver for HTTP requests, with retry support."""

    def __init__(
        self,
        hostname,
        ip,
    ):
        """Initialize the DNS resolver with retry configuration.

        Args:
            hostname: DNS entry to resolve.
            ip: Target IP address.
        """
        self.hostname = hostname
        self.ip = ip

        super().__init__(
            max_retries=DEFAULT_RETRIES,
            pool_connections=DEFAULT_POOLSIZE,
            pool_maxsize=DEFAULT_POOLSIZE,
            pool_block=DEFAULT_POOLBLOCK,
        )

    # Ignore pylint rule as this is the parent method signature
    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):  # pylint: disable=too-many-arguments, too-many-positional-arguments
        """Wrap HTTPAdapter send to modify the outbound request.

        Args:
            request: Outbound HTTP request.
            stream: argument used by parent method.
            timeout: argument used by parent method.
            verify: argument used by parent method.
            cert: argument used by parent method.
            proxies: argument used by parent method.

        Returns:
            Response: HTTP response after modification.
        """
        connection_pool_kwargs = self.poolmanager.connection_pool_kw

        result = urlparse(request.url)
        if result.hostname == self.hostname:
            ip = self.ip
            if result.scheme == "http" and ip:
                request.url = request.url.replace(
                    "http://" + result.hostname,
                    "http://" + ip,
                )
                connection_pool_kwargs["server_hostname"] = result.hostname
                request.headers["Host"] = result.hostname
            elif result.scheme == "https" and ip:
                request.url = request.url.replace(
                    "https://" + result.hostname,
                    "https://" + ip,
                )
                connection_pool_kwargs["server_hostname"] = result.hostname
                connection_pool_kwargs["assert_hostname"] = result.hostname
                request.headers["Host"] = result.hostname
            else:
                connection_pool_kwargs.pop("server_hostname", None)
                connection_pool_kwargs.pop("assert_hostname", None)

        return super().send(request, stream, timeout, verify, cert, proxies)


@retry(
    stop=stop_after_delay(180),
    wait=wait_fixed(5),
    retry=retry_if_exception_type((AssertionError, requests.exceptions.RequestException)),
    reraise=True,
)
def assert_gateway_route_response(
    gateway_address: str,
    hostname: str | None,
    path: str,
    *,
    scheme: str = "https",
    expected_status: int = 200,
    body_contains: str | None = None,
    allow_redirects: bool = True,
) -> requests.Response:
    """Get a gateway route and assert expected response, retrying while dataplane converges."""
    session = requests.Session()
    if hostname is not None:
        # Resolve the hostname to the gateway IP so the Host header and TLS SNI carry it,
        # which hostname-scoped gateway listeners require to route correctly.
        session.mount(f"{scheme}://{hostname}", DNSResolverAdapter(hostname, gateway_address))
        url = f"{scheme}://{hostname}{path}"
    else:
        url = f"{scheme}://{gateway_address}{path}"

    response = session.get(
        url,
        verify=False,
        timeout=10,
        allow_redirects=allow_redirects,
    )

    assert response.status_code == expected_status, (
        f"Failed to route to {hostname}: status={response.status_code}, "
        f"expected={expected_status}, body={response.text!r}"
    )
    if body_contains is not None:
        assert body_contains in response.text, (
            f"Expected response body for {hostname} to contain {body_contains!r}, "
            f"body={response.text!r}"
        )

    return response


def get_gateway_ip(juju: jubilant.Juju, gateway_api_integrator: str) -> str:
    """Get the gateway IP from the charm status message.

    Args:
        juju: The jubilant Juju instance.
        gateway_api_integrator: The gateway-api-integrator app name.

    Returns:
        The gateway IP address.
    """
    status = juju.status()
    app_status = status.apps[gateway_api_integrator]
    message = app_status.app_status.message
    if "gateway address" in message.lower():
        parts = message.split()
        try:
            candidate = parts[2]
            ipaddress.IPv4Address(candidate)
            return candidate
        except (IndexError, ipaddress.AddressValueError):
            return ""
    return ""
