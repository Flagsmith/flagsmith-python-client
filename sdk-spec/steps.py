"""
Steps for the Flagsmith SDK behavioural spec: https://github.com/Flagsmith/sdk-spec

Each function implements the Gherkin step in the comment above it.
"""

from flagsmith import Flagsmith
from flagsmith.models import Flags


def as_spec_flags(flags: Flags) -> list[dict]:
    return [
        {"feature": flag.feature_name, "enabled": flag.enabled, "value": flag.value}
        for flag in flags.all_flags()
    ]


# Given an SDK client for the environment
def create_client(environment_key: str, api_url: str) -> Flagsmith:
    return Flagsmith(environment_key=environment_key, api_url=api_url)


# When the application gets the environment flags
def get_environment_flags(flagsmith: Flagsmith) -> list[dict]:
    return as_spec_flags(flagsmith.get_environment_flags())


# When the application gets the flags for identity "{identifier}" with traits:
def get_identity_flags(
    flagsmith: Flagsmith, identifier: str, traits: dict
) -> list[dict]:
    return as_spec_flags(flagsmith.get_identity_flags(identifier, traits=traits))
