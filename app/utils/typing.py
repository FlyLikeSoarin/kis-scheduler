from typing import Any, Iterable

from enum import Enum


class ChoicesEnum(Enum):

    @classmethod
    def choices(cls) -> Iterable[tuple[Any, str]]:
        return tuple((i.value, i.name) for i in cls)