# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the charm."""
from ops import testing

from charm import GatewayAPICharm


def test_dns_record(base_state: dict) -> None:
    """
    arrange: Charm is initialized with a mock state.
    act: Run reconcile via the start event.
    assert: The charm updates the dns-record relation with the expected DNS entries.
    """
    ctx = testing.Context(GatewayAPICharm)
    state = testing.State(**base_state)
    ctx.run(ctx.on.start(), state)
    mock_dns_entry_str = (
        '[{"domain": "gateway.internal", '
        '"host_label": "www", '
        '"ttl": 600, '
        '"record_class": "IN", '
        '"record_type": "A", '
        '"record_data": "1.2.3.4", '
        '"uuid": "3ffc8151-8357-5348-9c57-0a585800a032"}]'
    )
    assert list(state.relations)[0].local_app_data["dns_entries"] == mock_dns_entry_str
