"""Deep merge utility for configuration dictionaries."""

import copy
from typing import Any


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base, returning a new dict.

    - Nested dicts are merged recursively.
    - Non-dict override values replace base values.
    - Disjoint keys from both dicts are preserved.
    - Neither input dict is mutated (uses deepcopy).
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result
