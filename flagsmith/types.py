import typing
from datetime import datetime

from flag_engine.context.types import EvaluationContext
from flag_engine.engine import ContextValue
from flag_engine.result.types import EvaluationResult, FlagResult
from typing_extensions import NotRequired, TypeAlias

_JsonScalarType: TypeAlias = typing.Union[
    int,
    str,
    float,
    bool,
    None,
]
JsonType: TypeAlias = typing.Union[
    _JsonScalarType,
    typing.Dict[str, "JsonType"],
    typing.List["JsonType"],
]


class StreamEvent(typing.TypedDict):
    updated_at: datetime


class TraitConfig(typing.TypedDict):
    value: ContextValue
    transient: bool


TraitMapping: TypeAlias = typing.Mapping[str, typing.Union[ContextValue, TraitConfig]]


class ApplicationMetadata(typing.TypedDict):
    name: NotRequired[str]
    version: NotRequired[str]


class SegmentMetadata(typing.TypedDict):
    flagsmith_id: NotRequired[int]
    """The ID of the segment used in Flagsmith API."""
    source: NotRequired[typing.Literal["api", "identity_overrides"]]
    """The source of the segment, e.g. 'api', 'identity_overrides'."""


class FeatureMetadata(typing.TypedDict):
    flagsmith_id: NotRequired[int]
    """The ID of the feature used in Flagsmith API."""


SDKEvaluationContext = EvaluationContext[SegmentMetadata, FeatureMetadata]
SDKEvaluationResult = EvaluationResult[SegmentMetadata, FeatureMetadata]
SDKFlagResult = FlagResult[FeatureMetadata]
