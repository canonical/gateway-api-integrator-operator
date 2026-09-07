# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for TLS behavior."""

import tempfile

import jubilant
import lightkube
import pytest
import tenacity
from helper import get_gateway_resource, get_ingress_url_for_application, wait_for_response


def _get_certificate_action_result(
    juju: jubilant.Juju, application: str, hostname: str
) -> dict[str, str]:
    """Fetch certificate data via the charm action."""
    result = juju.run(
        f"{application}/leader",
        "get-certificate",
        {"hostname": hostname},
    )
    return {
        "certificate": result.results["certificate"],
        "ca": result.results["ca"],
    }


@pytest.mark.abort_on_fail
def test_tls_certificate_rotates_after_csr_subject_attributes_change(
    juju: jubilant.Juju,
    configured_application_with_tls: str,
    ingress_requirer_application: str,
    certificate_provider_application: str,
    lightkube_client: lightkube.Client,
):
    """Changing CSR subject attributes should rotate the served TLS certificate."""
    application = configured_application_with_tls

    gateway = get_gateway_resource(lightkube_client, application)
    gateway_lb_ip = gateway.status["addresses"][0]["value"]  # type: ignore
    ingress_url = get_ingress_url_for_application(
        ingress_requirer_application, configured_application_with_tls, juju
    )

    old = _get_certificate_action_result(juju, application, ingress_url.netloc)

    juju.config(
        application,
        {
            "csr-subject-attributes": (
                "C=DE, ST=Hesse, L=Frankfurt, O=Canonical, "
                "OU=Engineering, emailAddress=ops@example.com"
            )
        },
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status,
            application,
            ingress_requirer_application,
            certificate_provider_application,
        ),
        delay=5,
        error=jubilant.any_error,
    )

    @tenacity.retry(stop=tenacity.stop_after_delay(180), wait=tenacity.wait_fixed(5), reraise=True)
    def _wait_for_rotated_certificate() -> dict[str, str]:
        new = _get_certificate_action_result(juju, application, ingress_url.netloc)
        assert new["certificate"] != old["certificate"]
        return new

    rotated = _wait_for_rotated_certificate()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".pem") as ca_bundle:
        ca_bundle.write(rotated["ca"])
        ca_bundle.flush()

        wait_for_response(
            f"https://{gateway_lb_ip}{ingress_url.path}",
            hostname=ingress_url.netloc,
            ip=gateway_lb_ip,
            expected_status=200,
            body_contains="Welcome to flask-k8s Charm",
            verify=ca_bundle.name,
            timeout=10,
        )
