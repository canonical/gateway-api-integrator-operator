# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""gateway-api-integrator charm base exceptions."""


class CharmStateValidationBaseError(Exception):
    """Exception raised when charm state data validation failed."""


class ResourceManagementBaseError(Exception):
    """Exception raised when managing k8s resources."""


class DNSRecordRequestsNotReadyError(Exception):
    """Exception raised when DNS record requests depend on transient state."""


class DNSRecordRequestsInvalidError(Exception):
    """Exception raised when one or more DNS record requests are invalid."""
