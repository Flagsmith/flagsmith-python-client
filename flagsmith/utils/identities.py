import typing

from flagsmith.types import JsonType, TraitMapping


def generate_identity_data(
    identifier: str,
    traits: TraitMapping,
    *,
    transient: bool,
) -> JsonType:
    identity_data: typing.Dict[str, JsonType] = {"identifier": identifier}
    traits_data: typing.List[JsonType] = []
    for trait_key, trait_value in traits.items():
        trait_data: typing.Dict[str, JsonType] = {"trait_key": trait_key}
        if isinstance(trait_value, dict):
            trait_data["trait_value"] = trait_value["value"]
            if trait_value.get("transient"):
                trait_data["transient"] = True
        else:
            trait_data["trait_value"] = trait_value
        traits_data.append(trait_data)
    identity_data["traits"] = traits_data
    if transient:
        identity_data["transient"] = True
    return identity_data
