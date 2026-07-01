# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Shared helpers for e2e tests."""

import ipaddress

import httpx
import jubilant
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_fixed


@retry(
    stop=stop_after_delay(180),
    wait=wait_fixed(5),
    retry=retry_if_exception_type((AssertionError, httpx.RequestError)),
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
) -> httpx.Response:
    """Get a gateway route and assert expected response, retrying while dataplane converges."""
    url = f"{scheme}://{hostname if hostname else gateway_address}{path}"
    # When a hostname is given, send it as Host header and TLS SNI so that
    # hostname-scoped gateway listeners route the request correctly.
    extensions = {"sni_hostname": hostname.encode()} if hostname else {}
    headers = {"Host": hostname} if hostname else {}
    with httpx.Client(verify=False) as client:
        response = client.send(
            httpx.Request("GET", url, headers=headers, extensions=extensions),
            follow_redirects=allow_redirects,
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
