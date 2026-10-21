"""
Steps for the Flagsmith SDK behavioural spec: https://github.com/Flagsmith/sdk-spec

Each function implements the Gherkin step in the comment above it.
"""

import typing

from flagsmith import Flagsmith
from flagsmith.models import Flags
from flagsmith.types import TraitMapping

SpecFlag = dict[str, typing.Any]


def as_spec_flags(flags: Flags) -> list[SpecFlag]:
    return [
        {"feature": flag.feature_name, "enabled": flag.enabled, "value": flag.value}
        for flag in flags.all_flags()
    ]


# Create the SDK client
def create_client(environment_key: str, api_url: str) -> Flagsmith:
    return Flagsmith(environment_key=environment_key, api_url=api_url)


# When the application gets the environment flags
def get_environment_flags(flagsmith: Flagsmith) -> list[SpecFlag]:
    return as_spec_flags(flagsmith.get_environment_flags())


# When the application gets the flags for identity "{identifier}" with traits:
def get_identity_flags(
    flagsmith: Flagsmith, identifier: str, traits: TraitMapping
) -> list[SpecFlag]:
    return as_spec_flags(flagsmith.get_identity_flags(identifier, traits=traits))


# When the application calls testChange
def call_test_change(flagsmith: Flagsmith) -> str:
    """The spec's minimal step, which checks that this SDK picks up newly added steps."""
    return "testChange"
