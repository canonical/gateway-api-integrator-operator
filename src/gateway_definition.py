# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""gateway-api-integrator gateway definition."""

from typing import Union

import ops


def get_config(charm: ops.CharmBase, field: str) -> Union[str, float, int, bool, None]:
    """Get data from charm config.

    Args:
        charm: The charm.
        field: Config field.

    Returns:
        The field's content.
    """
    # Config fields with a default of None don't appear in the dict
    config_data = charm.config.get(field, None)
    return config_data
