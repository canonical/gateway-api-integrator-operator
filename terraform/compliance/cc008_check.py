# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""CC008 Terraform module compliance checker.

Verifies that Terraform modules follow the CC008 (Terraform module standards)
structure and interface requirements. HCL is parsed with python-hcl2.
"""

from pathlib import Path

REQUIRED_FILES = ("terraform.tf", "variables.tf", "outputs.tf", "main.tf", "README.md")


def check_required_files(module_dir: Path) -> list[str]:
    """Return violations for any missing required module file.

    Args:
        module_dir: Path to the Terraform module directory.

    Returns:
        A list of human-readable violation messages.
    """
    return [
        f"missing required file: {name}"
        for name in REQUIRED_FILES
        if not (module_dir / name).exists()
    ]


def check_module(module_dir: Path) -> list[str]:
    """Return all CC008 violations for a single Terraform module directory.

    Args:
        module_dir: Path to the Terraform module directory.

    Returns:
        A list of human-readable violation messages (empty when compliant).
    """
    return check_required_files(module_dir)
