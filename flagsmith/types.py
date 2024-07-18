import typing

_JsonScalarType = typing.Union[
    int,
    str,
    float,
    bool,
    None,
]
JsonType = typing.Union[
    _JsonScalarType,
    typing.Dict[str, "JsonType"],
    typing.List["JsonType"],
]
