# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for gateway-route v1 interface library."""

import json
from typing import ClassVar

import pytest
from charms.gateway_api_integrator.v1.gateway_route import (
    GATEWAY_ROUTE_RELATION_NAME,
    GatewayRouteInvalidRelationDataError,
    GatewayRouteProvider,
    GatewayRouteRequirer,
    HttpsMode,
    valid_fqdn,
)
from ops import testing
from ops.charm import CharmBase

# --- Minimal test charms ---


class ProviderCharm(CharmBase):
    """Minimal charm for testing the provider side."""

    META: ClassVar[dict] = {
        "name": "provider-charm",
        "provides": {GATEWAY_ROUTE_RELATION_NAME: {"interface": "gateway-route"}},
    }

    def __init__(self, *args):
        super().__init__(*args)
        self.gateway_route = GatewayRouteProvider(self)


class RequirerCharm(CharmBase):
    """Minimal charm for testing the requirer side."""

    META: ClassVar[dict] = {
        "name": "requirer-charm",
        "requires": {GATEWAY_ROUTE_RELATION_NAME: {"interface": "gateway-route"}},
    }

    def __init__(self, *args):
        super().__init__(*args)
        self.gateway_route = GatewayRouteRequirer(self)


# --- valid_fqdn tests ---


class TestValidFqdn:
    """Tests for the valid_fqdn validator."""

    def test_valid_domain(self):
        """Test valid FQDN passes validation."""
        assert valid_fqdn("example.com") == "example.com"

    def test_valid_subdomain(self):
        """Test valid subdomain passes validation."""
        assert valid_fqdn("sub.example.com") == "sub.example.com"

    def test_invalid_domain_raises(self):
        """Test invalid domain raises ValueError."""
        with pytest.raises(ValueError, match="Invalid domain"):
            valid_fqdn("not a domain!")

    def test_tld_only_raises(self):
        """Test TLD-only value raises ValueError."""
        with pytest.raises(ValueError, match="Invalid domain"):
            valid_fqdn("com")


# --- Provider tests ---


class TestGatewayRouteProvider:
    """Tests for GatewayRouteProvider."""

    @pytest.fixture()
    def ctx(self):
        """Testing context for the provider charm."""
        return testing.Context(ProviderCharm, meta=ProviderCharm.META)

    def test_get_requirer_data_valid(self, ctx):
        """Test get_requirer_data returns validated data from a relation."""
        relation = testing.Relation(
            endpoint=GATEWAY_ROUTE_RELATION_NAME,
            interface="gateway-route",
            remote_app_data={
                "hostname": json.dumps("app.example.com"),
                "additional_hostnames": json.dumps(["alt.example.com"]),
            },
        )
        state = testing.State(leader=True, relations=[relation])

        with ctx(ctx.on.relation_changed(relation), state) as mgr:
            results = mgr.charm.gateway_route.get_requirer_data()
            assert len(results) == 1
            data = next(iter(results.values()))
            assert data.hostname == "app.example.com"
            assert data.additional_hostnames == ["alt.example.com"]

    def test_get_requirer_data_empty_is_valid_no_hostname(self, ctx):
        """Test get_requirer_data accepts a relation with no hostname as valid."""
        relation = testing.Relation(
            endpoint=GATEWAY_ROUTE_RELATION_NAME,
            interface="gateway-route",
            remote_app_data={},
        )
        state = testing.State(leader=True, relations=[relation])

        with ctx(ctx.on.relation_changed(relation), state) as mgr:
            results = mgr.charm.gateway_route.get_requirer_data()
            assert len(results) == 1
            data = next(iter(results.values()))
            assert data.hostname is None
            assert data.additional_hostnames == []
            assert len(mgr.charm.gateway_route._valid_relations) == 1

    def test_get_requirer_data_multiple_relations(self, ctx):
        """Test get_requirer_data returns data from all valid relations."""
        rel_1 = testing.Relation(
            endpoint=GATEWAY_ROUTE_RELATION_NAME,
            interface="gateway-route",
            remote_app_data={
                "hostname": json.dumps("one.example.com"),
                "additional_hostnames": json.dumps([]),
            },
        )
        rel_2 = testing.Relation(
            endpoint=GATEWAY_ROUTE_RELATION_NAME,
            interface="gateway-route",
            remote_app_data={
                "hostname": json.dumps("two.example.com"),
                "additional_hostnames": json.dumps([]),
            },
        )
        state = testing.State(leader=True, relations=[rel_1, rel_2])

        with ctx(ctx.on.relation_changed(rel_1), state) as mgr:
            results = mgr.charm.gateway_route.get_requirer_data()
            assert isinstance(results, dict)
            assert len(results) == 2
            for rel_id, data in results.items():
                assert isinstance(rel_id, int)
                assert data.hostname in {"one.example.com", "two.example.com"}
                assert data.additional_hostnames == []

    def test_get_requirer_data_skips_invalid(self, ctx):
        """Test get_requirer_data skips relations with invalid data."""
        valid_rel = testing.Relation(
            endpoint=GATEWAY_ROUTE_RELATION_NAME,
            interface="gateway-route",
            remote_app_data={
                "hostname": json.dumps("valid.example.com"),
                "additional_hostnames": json.dumps([]),
            },
        )
        invalid_rel = testing.Relation(
            endpoint=GATEWAY_ROUTE_RELATION_NAME,
            interface="gateway-route",
            remote_app_data={
                "hostname": json.dumps("not valid!"),
                "additional_hostnames": json.dumps([]),
            },
        )
        state = testing.State(leader=True, relations=[valid_rel, invalid_rel])

        with ctx(ctx.on.relation_changed(valid_rel), state) as mgr:
            results = mgr.charm.gateway_route.get_requirer_data()
            assert len(results) == 1
            assert next(iter(results.values())).hostname == "valid.example.com"

    def test_get_requirer_data_stores_valid_relations(self, ctx):
        """Test get_requirer_data populates _valid_relations."""
        rel = testing.Relation(
            endpoint=GATEWAY_ROUTE_RELATION_NAME,
            interface="gateway-route",
            remote_app_data={
                "hostname": json.dumps("app.example.com"),
                "additional_hostnames": json.dumps([]),
            },
        )
        state = testing.State(leader=True, relations=[rel])

        with ctx(ctx.on.relation_changed(rel), state) as mgr:
            mgr.charm.gateway_route.get_requirer_data()
            assert len(mgr.charm.gateway_route._valid_relations) == 1

    def test_publish_provider_data(self, ctx):
        """Test publish_provider_data writes to valid relations."""
        relation = testing.Relation(
            endpoint=GATEWAY_ROUTE_RELATION_NAME,
            interface="gateway-route",
            remote_app_data={
                "hostname": json.dumps("app.example.com"),
                "additional_hostnames": json.dumps([]),
            },
        )
        state = testing.State(leader=True, relations=[relation])

        with ctx(ctx.on.relation_changed(relation), state) as mgr:
            mgr.charm.gateway_route.get_requirer_data()
            mgr.charm.gateway_route.publish_provider_data(
                gateway_name="my-gateway",
                gateway_model="my-model",
                https_mode=HttpsMode.ENFORCED,
                gateway_address="10.0.0.1",
            )
            rel = mgr.charm.model.get_relation(GATEWAY_ROUTE_RELATION_NAME)
            app_data = rel.data[mgr.charm.app]
            assert json.loads(app_data["gateway_name"]) == "my-gateway"
            assert json.loads(app_data["gateway_model"]) == "my-model"
            assert json.loads(app_data["https_mode"]) == "enforced"
            assert json.loads(app_data["gateway_address"]) == "10.0.0.1"

    def test_publish_provider_data_skips_non_leader(self, ctx):
        """Test publish_provider_data does nothing when not leader."""
        relation = testing.Relation(
            endpoint=GATEWAY_ROUTE_RELATION_NAME,
            interface="gateway-route",
            remote_app_data={
                "hostname": json.dumps("app.example.com"),
                "additional_hostnames": json.dumps([]),
            },
        )
        state = testing.State(leader=False, relations=[relation])

        with ctx(ctx.on.relation_changed(relation), state) as mgr:
            mgr.charm.gateway_route.publish_provider_data(
                gateway_name="my-gateway",
                gateway_model="my-model",
                https_mode=HttpsMode.ENFORCED,
            )
            rel = mgr.charm.model.get_relation(GATEWAY_ROUTE_RELATION_NAME)
            assert "gateway_name" not in rel.data[mgr.charm.app]


# --- Requirer tests ---


class TestGatewayRouteRequirer:
    """Tests for GatewayRouteRequirer."""

    @pytest.fixture()
    def ctx(self):
        """Testing context for the requirer charm."""
        return testing.Context(RequirerCharm, meta=RequirerCharm.META)

    def test_publish_requirer_data(self, ctx):
        """Test publish_requirer_data writes hostname to relation."""
        relation = testing.Relation(
            endpoint=GATEWAY_ROUTE_RELATION_NAME,
            interface="gateway-route",
        )
        state = testing.State(leader=True, relations=[relation])

        with ctx(ctx.on.relation_changed(relation), state) as mgr:
            mgr.charm.gateway_route.publish_requirer_data(
                hostname="myapp.example.com",
                additional_hostnames=["alt.example.com"],
            )
            rel = mgr.charm.model.get_relation(GATEWAY_ROUTE_RELATION_NAME)
            app_data = rel.data[mgr.charm.app]
            assert json.loads(app_data["hostname"]) == "myapp.example.com"
            assert json.loads(app_data["additional_hostnames"]) == ["alt.example.com"]

    def test_publish_requirer_data_no_additional_hostnames(self, ctx):
        """Test publish_requirer_data with no additional hostnames."""
        relation = testing.Relation(
            endpoint=GATEWAY_ROUTE_RELATION_NAME,
            interface="gateway-route",
        )
        state = testing.State(leader=True, relations=[relation])

        with ctx(ctx.on.relation_changed(relation), state) as mgr:
            mgr.charm.gateway_route.publish_requirer_data(
                hostname="myapp.example.com",
            )
            rel = mgr.charm.model.get_relation(GATEWAY_ROUTE_RELATION_NAME)
            app_data = rel.data[mgr.charm.app]
            assert json.loads(app_data["hostname"]) == "myapp.example.com"
            assert json.loads(app_data["additional_hostnames"]) == []

    def test_publish_requirer_data_invalid_hostname_raises(self, ctx):
        """Test publish_requirer_data raises on invalid hostname."""
        relation = testing.Relation(
            endpoint=GATEWAY_ROUTE_RELATION_NAME,
            interface="gateway-route",
        )
        state = testing.State(leader=True, relations=[relation])

        with (
            ctx(ctx.on.relation_changed(relation), state) as mgr,
            pytest.raises(GatewayRouteInvalidRelationDataError),
        ):
            mgr.charm.gateway_route.publish_requirer_data(
                hostname="not valid!",
            )

    def test_publish_requirer_data_skips_non_leader(self, ctx):
        """Test publish_requirer_data does nothing when not leader."""
        relation = testing.Relation(
            endpoint=GATEWAY_ROUTE_RELATION_NAME,
            interface="gateway-route",
        )
        state = testing.State(leader=False, relations=[relation])

        with ctx(ctx.on.relation_changed(relation), state) as mgr:
            mgr.charm.gateway_route.publish_requirer_data(
                hostname="myapp.example.com",
            )
            rel = mgr.charm.model.get_relation(GATEWAY_ROUTE_RELATION_NAME)
            assert "hostname" not in rel.data[mgr.charm.app]

    def test_get_provider_data_valid(self, ctx):
        """Test get_provider_data returns validated data."""
        relation = testing.Relation(
            endpoint=GATEWAY_ROUTE_RELATION_NAME,
            interface="gateway-route",
            remote_app_data={
                "gateway_name": json.dumps("my-gateway"),
                "gateway_model": json.dumps("my-model"),
                "https_mode": json.dumps("enforced"),
            },
        )
        state = testing.State(leader=True, relations=[relation])

        with ctx(ctx.on.relation_changed(relation), state) as mgr:
            data = mgr.charm.gateway_route.get_provider_data()
            assert data is not None
            assert data.gateway_name == "my-gateway"
            assert data.gateway_model == "my-model"
            assert data.https_mode == HttpsMode.ENFORCED

    def test_get_provider_data_no_relation(self, ctx):
        """Test get_provider_data returns None without a relation."""
        state = testing.State(leader=True, relations=[])

        with ctx(ctx.on.start(), state) as mgr:
            data = mgr.charm.gateway_route.get_provider_data()
            assert data is None

    def test_get_provider_data_invalid_https_mode_raises(self, ctx):
        """Test get_provider_data raises on invalid https_mode."""
        relation = testing.Relation(
            endpoint=GATEWAY_ROUTE_RELATION_NAME,
            interface="gateway-route",
            remote_app_data={
                "gateway_name": json.dumps("my-gateway"),
                "gateway_model": json.dumps("my-model"),
                "https_mode": json.dumps("invalid-mode"),
            },
        )
        state = testing.State(leader=True, relations=[relation])

        with (
            ctx(ctx.on.relation_changed(relation), state) as mgr,
            pytest.raises(GatewayRouteInvalidRelationDataError),
        ):
            mgr.charm.gateway_route.get_provider_data()
