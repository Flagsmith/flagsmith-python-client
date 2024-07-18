import typing

from flag_engine.identities.traits.types import TraitValue

from flagsmith.types import JsonType


def generate_identity_data(
    identifier: str,
    traits: typing.Optional[typing.Mapping[str, TraitValue]],
    *,
    transient: bool,
    transient_traits: typing.Optional[typing.List[str]],
) -> JsonType:
    identity_data: typing.Dict[str, JsonType] = {"identifier": identifier}
    if traits:
        traits_data: typing.List[JsonType] = []
        transient_trait_keys = set(transient_traits) if transient_traits else set()
        for trait_key, trait_value in traits.items():
            trait_data: typing.Dict[str, JsonType] = {
                "trait_key": trait_key,
                "trait_value": trait_value,
            }
            if trait_key in transient_trait_keys:
                trait_data["transient"] = True
            traits_data.append(trait_data)
        identity_data["traits"] = traits_data
    if transient:
        identity_data["transient"] = True
    return identity_data
