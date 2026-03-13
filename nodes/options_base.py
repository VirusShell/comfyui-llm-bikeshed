"""Shared helpers for toggle-based options nodes."""

from __future__ import annotations

from typing import Any


def build_toggle_options(
    params: list[tuple[str, str, dict[str, Any]]],
    kwargs: dict[str, Any],
    options_in: dict[str, Any] | None = None,
) -> tuple[dict[str, Any]]:
    """Build an options dict from toggle-enabled parameters.

    Args:
        params: List of ``(name, dtype, opts)`` tuples defining available parameters.
        kwargs: Keyword arguments from the node's FUNCTION call, containing
            ``enable_{name}`` toggles and parameter values.
        options_in: Optional upstream options dict to merge into.

    Returns:
        Single-element tuple containing the merged options dict.
    """
    options = dict(options_in) if options_in else {}
    for name, _, _ in params:
        if kwargs.get(f"enable_{name}", False):
            options[name] = kwargs[name]
    return (options,)
