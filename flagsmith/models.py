import typing
from dataclasses import dataclass

from flag_engine.features.models import FeatureStateModel


@dataclass
class Flag:
    enabled: bool
    value: typing.Any
    feature_name: str

    @classmethod
    def from_feature_state_model(
        cls, feature_state_model: FeatureStateModel, identity_id: typing.Any = None
    ) -> "Flag":
        return Flag(
            enabled=feature_state_model.enabled,
            value=feature_state_model.get_value(identity_id=identity_id),
            feature_name=feature_state_model.feature.name,
        )

    @classmethod
    def from_api_flag(cls, flag_data: dict) -> "Flag":
        return Flag(
            enabled=flag_data["enabled"],
            value=flag_data["feature_state_value"],
            feature_name=flag_data["feature"]["name"],
        )


@dataclass
class Flags:
    flags: typing.Dict[str, Flag]

    @classmethod
    def from_feature_state_models(
        cls,
        feature_states: typing.List[FeatureStateModel],
        identity_id: typing.Any = None,
    ) -> "Flags":
        return cls(
            flags={
                feature_state.feature.name: Flag.from_feature_state_model(
                    feature_state, identity_id=identity_id
                )
                for feature_state in feature_states
            }
        )

    @classmethod
    def from_api_flags(cls, flags: typing.List[dict]) -> "Flags":
        return cls(
            flags={
                flag_data["feature"]["name"]: Flag.from_api_flag(flag_data)
                for flag_data in flags
            }
        )

    def all_flags(self) -> typing.List[Flag]:
        return list(self.flags.values())

    def get_flag(self, feature_name: str) -> typing.Optional[Flag]:
        return self.flags.get(feature_name)
