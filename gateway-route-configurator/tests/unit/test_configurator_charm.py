# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the Gateway Route Configurator Charm."""

from ops import testing

from charm import GatewayRouteConfiguratorCharm  # pylint: disable=no-name-in-module


def test_gateway_route(base_state: dict) -> None:
    """
    arrange: Charm is initialized with a mock state.
    act: Run reconcile via the config-changed event.
    assert: The charm updates the gateway-route relation with the expected data.
    """
    ctx = testing.Context(GatewayRouteConfiguratorCharm)
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.config_changed(), state)
    assert state.unit_status == testing.ActiveStatus("Ready")
    gateway_route_relation = next(
        rel for rel in state.relations if rel.endpoint == "gateway-route"
    )
    assert gateway_route_relation.local_app_data == {
        "hostname": '"testing-gateway.example.com"',
        "paths": '["[\\"/app1\\"", "\\"/app2\\"]"]',
        "model": '"testing-model"',
        "name": '"testing-ingress-app"',
        "port": "8080",
    }
    ingress_relation = next(rel for rel in state.relations if rel.endpoint == "ingress")
    assert ingress_relation.local_app_data == {
        "ingress": '{"url": "https://testing-gateway.example.com/app1"}'
    }


def test_gateway_route_no_hostname(base_state: dict) -> None:
    """
    arrange: Charm is initialized with a mock state without `hostname` config.
    act: Run reconcile via the config-changed event.
    assert: The charm goes into blocked state with the expected message.
    """
    ctx = testing.Context(GatewayRouteConfiguratorCharm)
    base_state["config"]["hostname"] = ""
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.config_changed(), state)
    assert state.unit_status == testing.BlockedStatus("Missing 'hostname' config")
    gateway_route_relation = next(
        rel for rel in state.relations if rel.endpoint == "gateway-route"
    )
    assert gateway_route_relation.local_app_data == {}


def test_gateway_route_invalid_hostname(base_state: dict) -> None:
    """
    arrange: Charm is initialized with a mock state with invalid `hostname` config.
    act: Run reconcile via the config-changed event.
    assert: The charm goes into blocked state with the expected message.
    """
    ctx = testing.Context(GatewayRouteConfiguratorCharm)
    base_state["config"]["hostname"] = "None"
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.config_changed(), state)
    assert state.unit_status == testing.BlockedStatus("Invalid hostname: None")
    gateway_route_relation = next(
        rel for rel in state.relations if rel.endpoint == "gateway-route"
    )
    assert gateway_route_relation.local_app_data == {}


def test_gateway_route_no_ingress_relation(base_state: dict, gateway_route_relation) -> None:
    """
    arrange: Charm is initialized with a mock state without `ingress` relation.
    act: Run reconcile via the config-changed event.
    assert: The charm goes into blocked state with the expected message.
    """
    ctx = testing.Context(GatewayRouteConfiguratorCharm)
    base_state["relations"] = [gateway_route_relation]
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.config_changed(), state)
    assert state.unit_status == testing.BlockedStatus("Missing 'ingress' relation")
    gateway_route_relation = next(
        rel for rel in state.relations if rel.endpoint == "gateway-route"
    )
    assert gateway_route_relation.local_app_data == {}


def test_gateway_route_no_gateway_route_relation(base_state: dict, ingress_relation) -> None:
    """
    arrange: Charm is initialized with a mock state without `gateway-route` relation.
    act: Run reconcile via the config-changed event.
    assert: The charm goes into blocked state with the expected message.
    """
    ctx = testing.Context(GatewayRouteConfiguratorCharm)
    base_state["relations"] = [ingress_relation]
    state = testing.State(**base_state)
    state = ctx.run(ctx.on.config_changed(), state)
    assert state.unit_status == testing.BlockedStatus("Missing 'gateway-route' relation")
