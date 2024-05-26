# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""nginx-ingress-integrator ingress definition."""

from typing import Union

import ops

from consts import BOOLEAN_CONFIG_FIELDS


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
    # A value of False is valid in these fields, so check it's not a null-value instead
    if field in BOOLEAN_CONFIG_FIELDS and (config_data is not None and config_data != ""):
        return config_data
    if config_data:
        return config_data

    return None
