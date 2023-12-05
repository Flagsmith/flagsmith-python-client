import typing


def generate_identities_data(
    identifier: str, traits: typing.Optional[typing.Mapping[str, typing.Any]] = None
) -> typing.Dict[str, typing.Any]:
    return {
        "identifier": identifier,
        "traits": [{"trait_key": k, "trait_value": v} for k, v in traits.items()]
        if traits
        else [],
    }
