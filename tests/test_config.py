"""Tests for config.merge.deep_merge utility."""

from config.merge import deep_merge


class TestDeepMergeNestedDicts:
    """Nested dicts are merged recursively, not replaced."""

    def test_nested_dict_merge(self) -> None:
        base = {"a": {"x": 1, "y": 2}}
        override = {"a": {"y": 99, "z": 3}}
        result = deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 99, "z": 3}}

    def test_deeply_nested_merge(self) -> None:
        base = {"a": {"b": {"c": 1, "d": 2}}}
        override = {"a": {"b": {"d": 99}}}
        result = deep_merge(base, override)
        assert result == {"a": {"b": {"c": 1, "d": 99}}}


class TestDeepMergeOverrideWins:
    """Non-dict override values replace base values."""

    def test_scalar_override(self) -> None:
        base = {"a": 1, "b": "hello"}
        override = {"a": 42, "b": "world"}
        result = deep_merge(base, override)
        assert result == {"a": 42, "b": "world"}

    def test_dict_replaced_by_scalar(self) -> None:
        base = {"a": {"nested": True}}
        override = {"a": "flat"}
        result = deep_merge(base, override)
        assert result == {"a": "flat"}

    def test_scalar_replaced_by_dict(self) -> None:
        base = {"a": "flat"}
        override = {"a": {"nested": True}}
        result = deep_merge(base, override)
        assert result == {"a": {"nested": True}}


class TestDeepMergeDisjointKeys:
    """Keys unique to each dict are preserved in result."""

    def test_disjoint_keys_preserved(self) -> None:
        base = {"a": 1, "b": 2}
        override = {"c": 3, "d": 4}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 2, "c": 3, "d": 4}

    def test_mixed_overlap_and_disjoint(self) -> None:
        base = {"a": 1, "b": 2}
        override = {"b": 99, "c": 3}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 99, "c": 3}


class TestDeepMergeEmptyInputs:
    """Empty dicts as base or override."""

    def test_empty_override_returns_base(self) -> None:
        base = {"a": 1, "b": {"c": 2}}
        result = deep_merge(base, {})
        assert result == base

    def test_empty_base_returns_override(self) -> None:
        override = {"a": 1, "b": {"c": 2}}
        result = deep_merge({}, override)
        assert result == override

    def test_both_empty(self) -> None:
        result = deep_merge({}, {})
        assert result == {}


class TestDeepMergeImmutability:
    """Neither input dict is mutated."""

    def test_base_not_mutated(self) -> None:
        base = {"a": {"x": 1}}
        override = {"a": {"x": 99}}
        deep_merge(base, override)
        assert base == {"a": {"x": 1}}

    def test_override_not_mutated(self) -> None:
        base = {"a": 1}
        override = {"b": [1, 2, 3]}
        deep_merge(base, override)
        assert override == {"b": [1, 2, 3]}

    def test_result_is_independent_copy(self) -> None:
        base = {"a": {"x": [1, 2]}}
        result = deep_merge(base, {})
        result["a"]["x"].append(3)
        assert base["a"]["x"] == [1, 2]
