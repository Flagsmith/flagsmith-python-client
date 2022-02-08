def generate_identities_data(identifier: str, traits: dict = None):
    return {
        "identifier": identifier,
        "traits": [{"trait_key": k, "trait_value": v} for k, v in traits.items()],
    }
