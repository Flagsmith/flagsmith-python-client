import typing

from flag_engine.identities.traits.types import TraitValue

Identity = typing.TypedDict(
    "Identity",
    {"identifier": str, "traits": typing.List[typing.Mapping[str, TraitValue]]},
)


def generate_identities_data(
    identifier: str, traits: typing.Optional[typing.Mapping[str, TraitValue]] = None
) -> Identity:
    return {
        "identifier": identifier,
        "traits": (
            [{"trait_key": k, "trait_value": v} for k, v in traits.items()]
            if traits
            else []
        ),
    }
