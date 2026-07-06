(changelog)=

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Each revision is versioned by the date of the revision.

## 2026-07-06

- Removed the souce code for the `gateway-route-configurator` charm that is replaced by the `ingress-configurator-charm`

## 2026-06-26

- Fixed a bug where multiple `gateway-route` relations with enforced HTTPS caused the gateway to become unreachable. The fix creates one HTTPS Gateway listener per hostname.

## 2026-06-22

- Improved test coverage for both `ingress` and `gateway-route` mode.

## 2026-06-18

- Migrated the RTD documentation URL under the Canonical domain.

## 2026-06-11

- Removed support for `gateway-route` v0 library.
- Added support for `gateway-route` v1 library.
- Removed resource creation for `gateway-route` relations.
- Added support for multiple `gateway-route` relations.

## 2026-06-01

- Added v1 `gateway-route` interface library.

## 2026-04-02

- Updated the `documentation` keys in the `charmcraft.yaml` files to point
  to the documentation on RTD.

## 2026-03-23

- Added support for additional hostnames.

## 2025-01-08

- Added project section to `pyproject.toml`.

## 2025-09-01

- Added security overview documentation.

## 2025-08-22

- Added changelog for tracking user-relevant changes.
