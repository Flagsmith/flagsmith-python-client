import typing

from flag_engine.segments.types import ConditionOperator, RuleType
from typing_extensions import NotRequired


class SegmentConditionModel(typing.TypedDict):
    operator: ConditionOperator
    property_: str
    value: str


class SegmentRuleModel(typing.TypedDict):
    conditions: "list[SegmentConditionModel]"
    rules: "list[SegmentRuleModel]"
    type: RuleType


class SegmentModel(typing.TypedDict):
    id: int
    name: str
    rules: list[SegmentRuleModel]
    feature_states: "NotRequired[list[FeatureStateModel]]"


class ProjectModel(typing.TypedDict):
    segments: list[SegmentModel]


class FeatureModel(typing.TypedDict):
    id: int
    name: str


class FeatureSegmentModel(typing.TypedDict):
    priority: int


class MultivariateFeatureOptionModel(typing.TypedDict):
    value: str


class MultivariateFeatureStateValueModel(typing.TypedDict):
    id: typing.Optional[int]
    multivariate_feature_option: MultivariateFeatureOptionModel
    mv_fs_value_uuid: str
    percentage_allocation: float


class FeatureStateModel(typing.TypedDict):
    enabled: bool
    feature_segment: NotRequired[FeatureSegmentModel]
    feature_state_value: object
    feature: FeatureModel
    featurestate_uuid: str
    multivariate_feature_state_values: list[MultivariateFeatureStateValueModel]


class IdentityModel(typing.TypedDict):
    identifier: str
    identity_features: list[FeatureStateModel]


class EnvironmentModel(typing.TypedDict):
    api_key: str
    feature_states: list[FeatureStateModel]
    identity_overrides: list[IdentityModel]
    name: str
    project: ProjectModel
