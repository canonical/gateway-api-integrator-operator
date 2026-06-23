# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for charm deploy."""

import logging

import jubilant
import lightkube
import pytest
import requests
from helper import (
    get_gateway_resource,
    get_ingress_url_for_application,
    wait_for_response,
)

logger = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
def test_ingress_enforced_mode(
    juju: jubilant.Juju,
    configured_application_with_tls: str,
    ingress_requirer_application: str,
    lightkube_client: lightkube.Client,
):
    """Test ingress with enforce-https=True (default) and TLS present.

    Assert that:
    - HTTP requests redirect (301) to HTTPS.
    - Invalid HTTPS routes return 404.
    - Valid HTTPS routes return 200 and route to the backend.
    """
    application = configured_application_with_tls
    juju.integrate(application, f"{ingress_requirer_application}:ingress")
    juju.wait(
        lambda status: jubilant.all_active(status, ingress_requirer_application, application),
        timeout=600,
    )

    gateway = get_gateway_resource(lightkube_client, application)
    gateway_lb_ip = gateway.status["addresses"][0]["value"]  # type: ignore

    ingress_url = get_ingress_url_for_application(ingress_requirer_application, juju)

    # HTTP should redirect to HTTPS
    wait_for_response(
        f"http://{gateway_lb_ip}{ingress_url.path}",
        hostname=ingress_url.netloc,
        ip=gateway_lb_ip,
        expected_status=301,
        allow_redirects=False,
        timeout=10,
    )

    wait_for_response(
        f"https://{gateway_lb_ip}/invalid",
        hostname=ingress_url.netloc,
        ip=gateway_lb_ip,
        expected_status=404,
        verify=False,  # nosec - calling charm ingress URL
        timeout=10,
    )

    wait_for_response(
        f"https://{gateway_lb_ip}{ingress_url.path}",
        hostname=ingress_url.netloc,
        ip=gateway_lb_ip,
        expected_status=200,
        body_contains="Welcome to flask-k8s Charm",
        verify=False,  # nosec - calling charm ingress URL
        timeout=10,
    )


@pytest.mark.abort_on_fail
def test_ingress_enabled_mode(
    juju: jubilant.Juju,
    configured_application_with_tls: str,
    ingress_requirer_application: str,
    lightkube_client: lightkube.Client,
):
    """Test ingress with enforce-https=False and TLS present.

    Assert that:
    - HTTP requests route to the backend.
    - HTTPS requests route to the backend.
    """
    application = configured_application_with_tls
    juju.config(application, {"enforce-https": "false"})
    juju.wait(
        lambda status: jubilant.all_active(status, application, ingress_requirer_application),
        timeout=600,
    )

    gateway = get_gateway_resource(lightkube_client, application)
    gateway_lb_ip = gateway.status["addresses"][0]["value"]  # type: ignore

    ingress_url = get_ingress_url_for_application(ingress_requirer_application, juju)

    wait_for_response(
        f"http://{gateway_lb_ip}{ingress_url.path}",
        hostname=ingress_url.netloc,
        ip=gateway_lb_ip,
        expected_status=200,
        body_contains="Welcome to flask-k8s Charm",
        timeout=10,
    )
    wait_for_response(
        f"https://{gateway_lb_ip}{ingress_url.path}",
        hostname=ingress_url.netloc,
        ip=gateway_lb_ip,
        expected_status=200,
        body_contains="Welcome to flask-k8s Charm",
        verify=False,  # nosec - self-signed certificate
        timeout=10,
    )


@pytest.mark.abort_on_fail
def test_ingress_disabled_mode(
    juju: jubilant.Juju,
    configured_application_with_tls: str,
    certificate_provider_application: str,
    ingress_requirer_application: str,
    lightkube_client: lightkube.Client,
):
    """Test ingress with enforce-https=False and TLS relation removed.

    Assert that:
    - HTTP requests route to the backend.
    - HTTPS is not available (raises ConnectionError).
    """
    application = configured_application_with_tls
    juju.remove_relation(
        f"{application}:certificates",
        f"{certificate_provider_application}:certificates",
    )
    juju.wait(
        lambda status: jubilant.all_active(status, application, ingress_requirer_application),
        timeout=600,
    )

    gateway = get_gateway_resource(lightkube_client, application)
    gateway_lb_ip = gateway.status["addresses"][0]["value"]  # type: ignore

    ingress_url = get_ingress_url_for_application(ingress_requirer_application, juju)

    wait_for_response(
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
