import typing

import pytest

from flagsmith.models import (
    DefaultFlag,
    Flag,
    Flags,
    build_segment_overrides_index,
)
from flagsmith.types import (
    SDKEvaluationContext,
    SDKEvaluationResult,
    SDKFlagResult,
)


def test_flag_from_evaluation_result() -> None:
    # Given
    flag_result: SDKFlagResult = {
        "enabled": True,
        "name": "test_feature",
        "reason": "DEFAULT",
        "value": "test-value",
        "metadata": {"id": 123},
    }

    # When
    flag = Flag.from_evaluation_result(flag_result)

    # Then
    assert flag.enabled is True
    assert flag.value == "test-value"
    assert flag.feature_name == "test_feature"
    assert flag.feature_id == 123
    assert flag.is_default is False


@pytest.mark.parametrize(
    "flags_result,expected_names",
    [
        ({}, []),
        (
            {
                "feature1": {
                    "enabled": True,
                    "name": "feature1",
                    "reason": "DEFAULT",
                    "value": "value1",
                    "metadata": {"id": 1},
                }
            },
            ["feature1"],
        ),
        (
            {
                "feature1": {
                    "enabled": True,
                    "name": "feature1",
                    "reason": "DEFAULT",
                    "value": "value1",
                    "metadata": {"id": 1},
                }
            },
            ["feature1"],
        ),
        (
            {
                "feature1": {
                    "enabled": True,
                    "name": "feature1",
                    "reason": "DEFAULT",
                    "value": "value1",
                    "metadata": {"id": 1},
                },
                "feature2": {
                    "enabled": True,
                    "name": "feature2",
                    "reason": "DEFAULT",
                    "value": "value2",
                    "metadata": {"id": 2},
                },
                "feature3": {
                    "enabled": True,
                    "name": "feature3",
                    "reason": "DEFAULT",
                    "value": 42,
                    "metadata": {"id": 3},
                },
            },
            ["feature1", "feature2", "feature3"],
        ),
    ],
)
def test_flags_from_evaluation_result(
    flags_result: typing.Dict[str, SDKFlagResult],
    expected_names: typing.List[str],
) -> None:
    # Given
    evaluation_result: SDKEvaluationResult = {
        "flags": flags_result,
        "segments": [],
    }

    # When
    flags: Flags = Flags.from_evaluation_result(
        evaluation_result=evaluation_result,
        analytics_processor=None,
        default_flag_handler=None,
    )

    # Then
    assert set(flags.flags.keys()) == set(expected_names)
    assert set(flag.feature_name for flag in flags.flags.values()) == set(
        expected_names
    )


@pytest.mark.parametrize(
    "value,expected",
    [
        ("string", "string"),
        (42, 42),
        (3.14, 3.14),
        (True, True),
        (False, False),
        (None, None),
    ],
)
def test_flag_from_evaluation_result_value_types(
    value: typing.Any, expected: typing.Any
) -> None:
    # Given
    flag_result: SDKFlagResult = {
        "enabled": True,
        "name": "test_feature",
        "reason": "DEFAULT",
        "value": value,
        "metadata": {"id": 123},
    }

    # When
    flag = Flag.from_evaluation_result(flag_result)

    # Then
    assert flag.value == expected


def test_flag_from_evaluation_result_missing_metadata__raises_expected() -> None:
    # Given
    flag_result: SDKFlagResult = {
        "enabled": True,
        "name": "test_feature",
        "reason": "DEFAULT",
        "value": "test-value",
    }

    # When & Then
    with pytest.raises(ValueError):
        Flag.from_evaluation_result(flag_result)


def test_get_flag_without_pipeline_processor() -> None:
    flags = Flags(
        flags={
            "my_feature": Flag(
                enabled=True, value="v1", feature_name="my_feature", feature_id=1
            )
        },
    )
    flag = flags.get_flag("my_feature")
    assert flag.enabled is True


LazyContextFactory = typing.Callable[..., SDKEvaluationContext]


@pytest.fixture
def lazy_context_factory() -> LazyContextFactory:
    """Factory for minimal evaluation contexts used by the lazy-Flags tests.

    The returned context has a `target` feature with a single segment
    override (matches when `tier == segment_match_value`, priority 0)
    plus `extra_features` no-override "noise" features whose values
    should come straight off the base feature context.
    """

    def make(
        *,
        extra_features: int = 2,
        identity_trait_value: str = "premium",
        segment_match_value: str = "premium",
    ) -> SDKEvaluationContext:
        features: typing.Dict[str, typing.Any] = {
            "target": {
                "key": "target",
                "name": "target",
                "enabled": False,
                "value": "base-value",
                "metadata": {"id": 1},
            },
        }
        for i in range(extra_features):
            features[f"noise_{i}"] = {
                "key": f"noise_{i}",
                "name": f"noise_{i}",
                "enabled": True,
                "value": f"noise-value-{i}",
                "metadata": {"id": 100 + i},
            }
        return {
            "environment": {"key": "env-key", "name": "env"},
            "features": features,
            "segments": {
                "premium_segment": {
                    "key": "premium_segment",
                    "name": "premium_segment",
                    "rules": [
                        {
                            "type": "ALL",
                            "conditions": [
                                {
                                    "property": "tier",
                                    "operator": "EQUAL",
                                    "value": segment_match_value,
                                },
                            ],
                        }
                    ],
                    "overrides": [
                        {
                            "key": "target",
                            "name": "target",
                            "enabled": True,
                            "value": "premium-value",
                            "priority": 0.0,
                            "metadata": {"id": 1},
                        },
                    ],
                },
            },
            "identity": {
                "identifier": "user-1",
                "key": "env-key_user-1",
                "traits": {"tier": identity_trait_value},
            },
        }

    return make


@pytest.fixture
def lazy_context(
    lazy_context_factory: LazyContextFactory,
) -> SDKEvaluationContext:
    """Default evaluation context: identity matches the segment override."""
    return lazy_context_factory()


@pytest.fixture
def lazy_flags(lazy_context: SDKEvaluationContext) -> Flags:
    """Lazy `Flags` built from the default context, no analytics, no handler."""
    return Flags.from_evaluation_context(
        context=lazy_context,
        overrides_index=build_segment_overrides_index(lazy_context),
        analytics_processor=None,
        default_flag_handler=None,
    )


def test_lazy_flags__get_flag__applies_matching_segment_override(
    lazy_flags: Flags,
) -> None:
    # Given: identity matches the segment rule (default context).
    # When: we read the targeted feature.
    target = lazy_flags.get_flag("target")
    # Then: the override wins over the base feature value.
    assert target.enabled is True
    assert target.value == "premium-value"


def test_lazy_flags__get_flag__skips_non_matching_segment_override(
    lazy_context_factory: LazyContextFactory,
) -> None:
    # Given: segment rule requires tier == "premium" but identity has tier "free".
    ctx = lazy_context_factory(identity_trait_value="free")
    flags = Flags.from_evaluation_context(
        context=ctx,
        overrides_index=build_segment_overrides_index(ctx),
        analytics_processor=None,
        default_flag_handler=None,
    )

    # When: we read the targeted feature.
    target = flags.get_flag("target")

    # Then: the override doesn't win and base-value comes through.
    assert target.enabled is False
    assert target.value == "base-value"


def test_lazy_flags__get_flag__caches_per_feature(
    lazy_context_factory: LazyContextFactory,
) -> None:
    # Given: a context with several no-override features.
    ctx = lazy_context_factory(extra_features=5)
    flags = Flags.from_evaluation_context(
        context=ctx,
        overrides_index=build_segment_overrides_index(ctx),
        analytics_processor=None,
        default_flag_handler=None,
    )

    # When: we read a single feature once.
    flags.get_flag("noise_0")

    # Then: only that feature is populated in the cache.
    assert set(flags.flags.keys()) == {"noise_0"}

    # And: repeated reads return the same Flag instance, not a rebuild.
    first = flags.get_flag("noise_0")
    second = flags.get_flag("noise_0")
    assert first is second


def test_lazy_flags__all_flags__materialises_every_feature(
    lazy_context_factory: LazyContextFactory,
) -> None:
    # Given: a context with three no-override features plus the target.
    ctx = lazy_context_factory(extra_features=3)
    flags = Flags.from_evaluation_context(
        context=ctx,
        overrides_index=build_segment_overrides_index(ctx),
        analytics_processor=None,
        default_flag_handler=None,
    )

    # When: the caller asks for the full set.
    materialised = flags.all_flags()

    # Then: every feature in the context is present.
    names = {flag.feature_name for flag in materialised}
    assert names == {"target", "noise_0", "noise_1", "noise_2"}

    # And: a second call is a no-op — everything is already resolved.
    assert flags.all_flags() == materialised


def test_lazy_flags__missing_feature__falls_through_to_default_handler(
    lazy_context: SDKEvaluationContext,
) -> None:
    # Given: a Flags wired to a default-flag handler.
    def default(name: str) -> DefaultFlag:
        return DefaultFlag(enabled=False, value=f"default-for-{name}")

    flags = Flags.from_evaluation_context(
        context=lazy_context,
        overrides_index=build_segment_overrides_index(lazy_context),
        analytics_processor=None,
        default_flag_handler=default,
    )

    # When: we ask for a feature that isn't in the context.
    result = flags.get_flag("does_not_exist")

    # Then: the handler produces the default flag for that name.
    assert result.value == "default-for-does_not_exist"


def test_build_segment_overrides_index__indexes_only_overriding_segments(
    lazy_context: SDKEvaluationContext,
) -> None:
    # Given: a second segment with no overrides on top of the default context.
    assert lazy_context["segments"] is not None
    lazy_context["segments"]["no_override_segment"] = {
        "key": "no_override_segment",
        "name": "no_override_segment",
        "rules": [
            {
                "type": "ALL",
                "conditions": [
                    {"property": "tier", "operator": "EQUAL", "value": "premium"},
                ],
            }
        ],
    }

    # When: we build the reverse index.
    index = build_segment_overrides_index(lazy_context)

    # Then: only segments that actually carry an override appear.
    assert set(index) == {"target"}
    assert index["target"][0]["name"] == "premium_segment"
