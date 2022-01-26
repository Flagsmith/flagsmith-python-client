import typing
from dataclasses import dataclass

from flag_engine.features.models import FeatureStateModel

from flagsmith.analytics import AnalyticsProcessor
from flagsmith.exceptions import FlagsmithClientError


@dataclass
class Flag:
    enabled: bool
    value: typing.Any
    feature_name: str
    feature_id: int

    @classmethod
    def from_feature_state_model(
        cls, feature_state_model: FeatureStateModel, identity_id: typing.Any = None
    ) -> "Flag":
        return Flag(
            enabled=feature_state_model.enabled,
            value=feature_state_model.get_value(identity_id=identity_id),
            feature_name=feature_state_model.feature.name,
            feature_id=feature_state_model.feature.id,
        )

    @classmethod
    def from_api_flag(cls, flag_data: dict) -> "Flag":
        return Flag(
            enabled=flag_data["enabled"],
            value=flag_data["feature_state_value"],
            feature_name=flag_data["feature"]["name"],
            feature_id=flag_data["feature"]["id"],
        )


@dataclass
class Flags:
    flags: typing.Dict[str, Flag]
    _analytics_processor: AnalyticsProcessor = None

    @classmethod
    def from_feature_state_models(
        cls,
        feature_states: typing.List[FeatureStateModel],
        analytics_processor: AnalyticsProcessor,
        identity_id: typing.Any = None,
    ) -> "Flags":
        return cls(
            flags={
                feature_state.feature.name: Flag.from_feature_state_model(
                    feature_state, identity_id=identity_id
                )
                for feature_state in feature_states
            },
            _analytics_processor=analytics_processor,
        )

    @classmethod
    def from_api_flags(
        cls, flags: typing.List[dict], analytics_processor: AnalyticsProcessor
    ) -> "Flags":
        return cls(
            flags={
                flag_data["feature"]["name"]: Flag.from_api_flag(flag_data)
                for flag_data in flags
            },
            _analytics_processor=analytics_processor,
        )

    def all_flags(self) -> typing.List[Flag]:
        """
        Get a list of all Flag objects.

        :return: list of Flag objects.
        """
        return list(self.flags.values())

    def is_feature_enabled(self, feature_name: str) -> bool:
        """
        Check whether a given feature is enabled.

        :param feature_name: the name of the feature to check if enabled.
        :return: Boolean representing the enabled state of a given feature.
        :raises FlagsmithClientError: if feature doesn't exist
        """
        return self.get_flag(feature_name).enabled

    def get_feature_value(self, feature_name: str) -> typing.Any:
        """
        Get the value of a particular feature.

        :param feature_name: the name of the feature to retrieve the value of.
        :return: the value of the given feature.
        :raises FlagsmithClientError: if feature doesn't exist
        """
        return self.get_flag(feature_name).value

    def get_flag(self, feature_name: str) -> typing.Optional[Flag]:
        """
        Get a specific flag given the feature name.

        :param feature_name: the name of the feature to retrieve the flag for.
        :return: Flag object.
        :raises FlagsmithClientError: if feature doesn't exist
        """
        try:
            flag = self.flags[feature_name]
        except KeyError:
            raise FlagsmithClientError("Feature does not exist: %s" % feature_name)

        if self._analytics_processor:
            self._analytics_processor.track_feature(flag.feature_id)

        return flag
