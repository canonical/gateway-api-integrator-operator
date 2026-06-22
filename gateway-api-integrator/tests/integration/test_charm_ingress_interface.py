# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for charm deploy."""

import logging

import lightkube
import pytest
import requests
from conftest import TEST_EXTERNAL_HOSTNAME_CONFIG
from helper import (
    DNSResolverHTTPSAdapter,
    get_gateway_resource,
    get_http_route_resource,
    get_ingress_url_for_application,
)
from juju.application import Application
from pytest_operator.plugin import OpsTest
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_fixed

logger = logging.getLogger(__name__)
CREATED_BY_LABEL = "gateway-api-integrator.charm.juju.is/managed-by"


@retry(
    stop=stop_after_delay(180),
    wait=wait_fixed(5),
    retry=retry_if_exception_type((AssertionError, requests.exceptions.RequestException)),
    reraise=True,
)
def _wait_for_response(
    url: str,
    *,
    hostname: str,
    ip: str,
    expected_status: int,
    body_contains: str | None = None,
    timeout: int | float = 30,
    **kwargs,
) -> requests.Response:
    """Retry HTTP GET until expected status/body is observed."""
    session = requests.Session()
    session.mount("https://", DNSResolverHTTPSAdapter(hostname=hostname, ip=ip))
    headers = kwargs.pop("headers", {})
    headers.setdefault("Host", hostname)
    response = session.get(url, timeout=timeout, headers=headers, **kwargs)

    assert response.status_code == expected_status, (
        f"Unexpected status from {url}. "
        f"got={response.status_code}, expected={expected_status}, body={response.text!r}"
    )

    if body_contains:
        assert body_contains in response.text, (
            f"Expected response body from {url} to contain {body_contains!r}. "
            f"body={response.text!r}"
        )

    return response


@pytest.mark.abort_on_fail
async def test_ingress_enforced_mode(
    configured_application_with_tls: Application,
    ingress_requirer_application: Application,
    lightkube_client: lightkube.Client,
    ops_test: OpsTest,
):
    """Deploy the charm together with related charms.

    Assert on the unit status before any relations/configurations take place.
    """
    application = configured_application_with_tls
    await application.model.add_relation(
        application.name, f"{ingress_requirer_application.name}:ingress"
    )
    await application.model.wait_for_idle(
        apps=[ingress_requirer_application.name, application.name],
        idle_period=30,
        status="active",
    )

    gateway = get_gateway_resource(lightkube_client, application.name)
    gateway_lb_ip = gateway.status["addresses"][0]["value"]  # type: ignore
    assert gateway_lb_ip, "LB address not assigned to gateway"

    listeners = gateway.spec["listeners"]  # type: ignore
    listener_protocols = {(listener["protocol"], listener["port"]) for listener in listeners}
    assert ("HTTP", 80) in listener_protocols, "HTTP listener on port 80 not found"
    assert ("HTTPS", 443) in listener_protocols, "HTTPS listener on port 443 not found"

    http_route = get_http_route_resource(lightkube_client, application.name)
    redirect_filters = [
        f
        for rule in http_route.spec["rules"]  # type: ignore
        for f in rule.get("filters", [])
        if f.get("type") == "RequestRedirect"
    ]
    assert redirect_filters, "No RequestRedirect filter found in HTTP HTTPRoute"
    assert redirect_filters[0]["requestRedirect"]["scheme"] == "https"
    assert redirect_filters[0]["requestRedirect"]["statusCode"] == 301

    ingress_url = await get_ingress_url_for_application(ingress_requirer_application, ops_test)
    assert ingress_url.netloc == TEST_EXTERNAL_HOSTNAME_CONFIG
    assert ingress_url.path == f"/{application.model.name}-{ingress_requirer_application.name}"

    res = _wait_for_response(
        f"http://{gateway_lb_ip}{ingress_url.path}",
        hostname=ingress_url.netloc,
        ip=gateway_lb_ip,
        expected_status=301,
        allow_redirects=False,
        timeout=10,
    )
    assert res.headers["location"] == f"https://{ingress_url.netloc}:443{ingress_url.path}"

    _wait_for_response(
        f"https://{gateway_lb_ip}/invalid",
        hostname=ingress_url.netloc,
        ip=gateway_lb_ip,
        expected_status=404,
        verify=False,  # nosec - calling charm ingress URL
        timeout=10,
    )

    _wait_for_response(
        f"https://{gateway_lb_ip}{ingress_url.path}",
        hostname=ingress_url.netloc,
        ip=gateway_lb_ip,
        expected_status=200,
        body_contains="Welcome to flask-k8s Charm",
        verify=False,  # nosec - calling charm ingress URL
        timeout=10,
    )

    # Test HTTP redirect to HTTPS
    _wait_for_response(
        f"http://{gateway_lb_ip}{ingress_url.path}",
        hostname=ingress_url.netloc,
        ip=gateway_lb_ip,
        expected_status=200,
        body_contains="Welcome to flask-k8s Charm",
        allow_redirects=True,
        verify=False,  # nosec - self-signed cert after redirect to HTTPS
        timeout=10,
    )


@pytest.mark.abort_on_fail
async def test_ingress_enabled_mode(
    configured_application_with_tls: Application,
    ingress_requirer_application: Application,
    lightkube_client: lightkube.Client,
    ops_test: OpsTest,
):
    """Test ingress mode with enforce_https=False.

    Assert that both HTTP and HTTPS are accessible without redirect,
    and that no RequestRedirect filter is present on the HTTP HTTPRoute.
    """
    application = configured_application_with_tls
    await application.set_config({"enforce-https": "false"})
    await application.model.wait_for_idle(
        apps=[application.name, ingress_requirer_application.name],
        idle_period=30,
        status="active",
    )

    gateway = get_gateway_resource(lightkube_client, application.name)
    gateway_lb_ip = gateway.status["addresses"][0]["value"]  # type: ignore

    listeners = gateway.spec["listeners"]  # type: ignore
    listener_protocols = {(listener["protocol"], listener["port"]) for listener in listeners}
    assert ("HTTP", 80) in listener_protocols, "HTTP listener on port 80 not found"
    assert ("HTTPS", 443) in listener_protocols, "HTTPS listener on port 443 not found"

    http_route = get_http_route_resource(lightkube_client, application.name)
    redirect_filters = [
        f
        for rule in http_route.spec["rules"]  # type: ignore
        for f in rule.get("filters", [])
        if f.get("type") == "RequestRedirect"
    ]
    assert not redirect_filters, (
        "RequestRedirect filter should not be present when enforce-https is False"
    )

    ingress_url = await get_ingress_url_for_application(ingress_requirer_application, ops_test)

    _wait_for_response(
        f"http://{gateway_lb_ip}{ingress_url.path}",
        hostname=ingress_url.netloc,
        ip=gateway_lb_ip,
        expected_status=200,
        body_contains="Welcome to flask-k8s Charm",
        timeout=10,
    )
    _wait_for_response(
        f"https://{gateway_lb_ip}{ingress_url.path}",
        hostname=ingress_url.netloc,
        ip=gateway_lb_ip,
        expected_status=200,
        body_contains="Welcome to flask-k8s Charm",
        verify=False,  # nosec - self-signed certificate
        timeout=10,
    )


@pytest.mark.abort_on_fail
async def test_ingress_disabled_mode(
    configured_application_with_tls: Application,
    certificate_provider_application: Application,
    ingress_requirer_application: Application,
    lightkube_client: lightkube.Client,
    ops_test: OpsTest,
):
    """Test ingress mode with TLS relation removed.

    Assert that only the HTTP listener is present, HTTP traffic works,
    and HTTPS is no longer accessible.
    """
    application = configured_application_with_tls
    await application.destroy_relation(
        "certificates",
        f"{certificate_provider_application.name}:certificates",
    )
    await application.model.wait_for_idle(
        apps=[application.name, ingress_requirer_application.name],
        idle_period=30,
        status="active",
    )

    gateway = get_gateway_resource(lightkube_client, application.name)
    gateway_lb_ip = gateway.status["addresses"][0]["value"]  # type: ignore

    listeners = gateway.spec["listeners"]  # type: ignore
    listener_protocols = {(listener["protocol"], listener["port"]) for listener in listeners}
    assert ("HTTP", 80) in listener_protocols, "HTTP listener on port 80 not found"
    assert ("HTTPS", 443) not in listener_protocols, (
        "HTTPS listener should not be present without TLS relation"
    )

    ingress_url = await get_ingress_url_for_application(ingress_requirer_application, ops_test)

    _wait_for_response(
        f"http://{gateway_lb_ip}{ingress_url.path}",
        hostname=ingress_url.netloc,
        ip=gateway_lb_ip,
        expected_status=200,
        body_contains="Welcome to flask-k8s Charm",
        timeout=10,
    )
    with pytest.raises(requests.exceptions.ConnectionError):
        requests.get(
            f"https://{gateway_lb_ip}{ingress_url.path}",
            headers={"Host": ingress_url.netloc},
            verify=False,  # nosec
            timeout=10,
        )
