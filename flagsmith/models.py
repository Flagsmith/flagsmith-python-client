from __future__ import annotations

import typing
from dataclasses import dataclass, field

from flag_engine.result.types import EvaluationResult, FlagResult

from flagsmith.analytics import AnalyticsProcessor
from flagsmith.exceptions import FlagsmithFeatureDoesNotExistError


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
        flag: FlagResult,
    ) -> Flag:
        return Flag(
            enabled=flag["enabled"],
            value=flag["value"],
            feature_name=flag["name"],
            feature_id=int(flag["feature_key"]),
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
        evaluation_result: EvaluationResult,
        analytics_processor: typing.Optional[AnalyticsProcessor],
        default_flag_handler: typing.Optional[typing.Callable[[str], DefaultFlag]],
    ) -> Flags:
        return cls(
            flags={
                flag["name"]: Flag(
                    enabled=flag["enabled"],
                    value=flag["value"],
                    feature_name=flag["name"],
                    feature_id=int(flag["feature_key"]),
                )
                for flag in evaluation_result["flags"]
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
