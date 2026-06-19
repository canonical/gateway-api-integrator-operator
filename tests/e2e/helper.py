# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Shared helpers for e2e tests."""

import requests
import urllib3
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_fixed
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings when using verify=False
urllib3.disable_warnings(InsecureRequestWarning)


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
) -> requests.Response:
    """Get a gateway route and assert expected response, retrying while dataplane converges."""
    headers = {"Host": hostname} if hostname is not None else None
    response = requests.get(
        f"{scheme}://{gateway_address}{path}",
        verify=False,
        timeout=10,
        headers=headers,
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
