from __future__ import annotations

import typing
from dataclasses import dataclass, field

from flagsmith.analytics import AnalyticsProcessor
from flagsmith.exceptions import FlagsmithFeatureDoesNotExistError
from flagsmith.types import SDKEvaluationResult, SDKFlagResult


@dataclass
class BaseFlag:
    enabled: bool
    value: typing.Union[str, int, float, bool, None]


@dataclass
class DefaultFlag(BaseFlag):
    is_default: bool = field(default=True)


@dataclass
class Flag(BaseFlag):
    feature_id: int
    feature_name: str
    is_default: bool = field(default=False)

    @classmethod
    def from_evaluation_result(
        cls,
        flag_result: SDKFlagResult,
    ) -> Flag:
        if metadata := flag_result.get("metadata"):
            return Flag(
                enabled=flag_result["enabled"],
                value=flag_result["value"],
                feature_name=flag_result["name"],
                feature_id=metadata["flagsmith_id"],
            )
        raise ValueError(
            "FlagResult metadata is missing. Cannot create Flag instance. "
            "This means a bug in the SDK, please report it."
        )

    @classmethod
    def from_api_flag(cls, flag_data: typing.Mapping[str, typing.Any]) -> Flag:
        return Flag(
            enabled=flag_data["enabled"],
            value=flag_data["feature_state_value"],
            feature_name=flag_data["feature"]["name"],
            feature_id=flag_data["feature"]["id"],
        )


@dataclass
class Flags:
    flags: typing.Dict[str, Flag] = field(default_factory=dict)
    default_flag_handler: typing.Optional[typing.Callable[[str], DefaultFlag]] = None
    _analytics_processor: typing.Optional[AnalyticsProcessor] = None

    @classmethod
    def from_evaluation_result(
        cls,
        evaluation_result: SDKEvaluationResult,
        analytics_processor: typing.Optional[AnalyticsProcessor],
        default_flag_handler: typing.Optional[typing.Callable[[str], DefaultFlag]],
    ) -> Flags:
        return cls(
            flags={
                flag_name: flag
                for flag_name, flag_result in evaluation_result["flags"].items()
                if (flag := Flag.from_evaluation_result(flag_result))
            },
            default_flag_handler=default_flag_handler,
            _analytics_processor=analytics_processor,
        )

    @classmethod
    def from_api_flags(
        cls,
        api_flags: typing.Sequence[typing.Mapping[str, typing.Any]],
        analytics_processor: typing.Optional[AnalyticsProcessor],
        default_flag_handler: typing.Optional[typing.Callable[[str], DefaultFlag]],
    ) -> Flags:
        flags = {
            flag_data["feature"]["name"]: Flag.from_api_flag(flag_data)
            for flag_data in api_flags
        }

        return cls(
            flags=flags,
            default_flag_handler=default_flag_handler,
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

    def get_flag(self, feature_name: str) -> typing.Union[DefaultFlag, Flag]:
        """
        Get a specific flag given the feature name.

        :param feature_name: the name of the feature to retrieve the flag for.
        :return: DefaultFlag | Flag object.
        :raises FlagsmithClientError: if feature doesn't exist
        """
        try:
            flag = self.flags[feature_name]
        except KeyError:
            if self.default_flag_handler:
                return self.default_flag_handler(feature_name)
            raise FlagsmithFeatureDoesNotExistError(
                "Feature does not exist: %s" % feature_name
            )

        if self._analytics_processor and hasattr(flag, "feature_name"):
            self._analytics_processor.track_feature(flag.feature_name)

        return flag


@dataclass
class Segment:
    id: int
    name: str
