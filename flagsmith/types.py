import typing

from flag_engine.identities.traits.types import TraitValue
from typing_extensions import NotRequired, TypeAlias

_JsonScalarType: TypeAlias = typing.Union[
    int,
    str,
    float,
    bool,
    None,
]
JsonType: TypeAlias = typing.Union[
    _JsonScalarType,
    typing.Dict[str, "JsonType"],
    typing.List["JsonType"],
]


class TraitConfig(typing.TypedDict):
    value: TraitValue
    transient: bool


TraitMapping: TypeAlias = typing.Mapping[str, typing.Union[TraitValue, TraitConfig]]


class ApplicationMetadata(typing.TypedDict):
    name: NotRequired[str]
    version: NotRequired[str]
