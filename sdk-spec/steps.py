"""
Steps for the Flagsmith SDK behavioural spec: https://github.com/Flagsmith/sdk-spec

Each function implements the Gherkin step in the comment above it.
"""

import typing

from flagsmith import EventProcessorConfig, Flagsmith
from flagsmith.models import Flag, Flags
from flagsmith.types import TraitMapping

SpecFlag = dict[str, typing.Any]
EventValue = typing.Union[str, int, float, bool]


def as_spec_flag(flag: Flag) -> SpecFlag:
    return {"feature": flag.feature_name, "enabled": flag.enabled, "value": flag.value}


def as_spec_flags(flags: Flags) -> list[SpecFlag]:
    return [as_spec_flag(flag) for flag in flags.all_flags()]


# Create the SDK client
def create_client(environment_key: str, api_url: str) -> Flagsmith:
    return Flagsmith(environment_key=environment_key, api_url=api_url)


# Create the SDK client with events enabled
def create_client_with_events(
    environment_key: str, api_url: str, events_api_url: str
) -> Flagsmith:
    return Flagsmith(
        environment_key=environment_key,
        api_url=api_url,
        enable_events=True,
        event_processor_config=EventProcessorConfig(events_api_url=events_api_url),
    )


# When the application gets the environment flags
def get_environment_flags(flagsmith: Flagsmith) -> list[SpecFlag]:
    return as_spec_flags(flagsmith.get_environment_flags())


# When the application gets the flags for identity "{identifier}" with traits:
def get_identity_flags(
    flagsmith: Flagsmith, identifier: str, traits: TraitMapping
) -> list[SpecFlag]:
    return as_spec_flags(flagsmith.get_identity_flags(identifier, traits=traits))


# When the application gets the experiment flag "{feature}" for identity "{identifier}" with traits:
def get_experiment_flag(
    flagsmith: Flagsmith, feature: str, identifier: str, traits: TraitMapping
) -> list[SpecFlag]:
    flag = flagsmith.get_experiment_flag(feature, identifier, traits)
    return [as_spec_flag(flag)] if isinstance(flag, Flag) else []


# When the application tracks event "{event}" for identity "{identifier}" with value {value} and metadata:
def track_event(
    flagsmith: Flagsmith,
    event: str,
    identifier: str,
    value: EventValue,
    metadata: dict[str, typing.Any],
) -> None:
    flagsmith.track_event(event, identifier=identifier, value=value, metadata=metadata)


# When the application tracks an exposure of feature "{feature}" for identity "{identifier}" with value {value} and metadata:
def track_exposure_event(
    flagsmith: Flagsmith,
    feature: str,
    identifier: str,
    value: EventValue,
    metadata: dict[str, typing.Any],
) -> None:
    flagsmith.track_exposure_event(
        feature, identifier=identifier, value=value, metadata=metadata
    )
