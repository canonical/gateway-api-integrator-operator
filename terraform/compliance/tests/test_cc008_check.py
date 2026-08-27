# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the CC008 Terraform compliance checker."""

from pathlib import Path

import hcl2

import cc008_check


def test_missing_required_files_are_reported(tmp_path: Path) -> None:
    module = tmp_path / "empty"
    module.mkdir()

    violations = cc008_check.check_required_files(module)

    assert "missing required file: terraform.tf" in violations
    assert "missing required file: variables.tf" in violations
    assert "missing required file: outputs.tf" in violations
    assert "missing required file: main.tf" in violations
    assert "missing required file: README.md" in violations
