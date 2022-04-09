from enum import Enum
from typing import Any, Iterable


class ChoicesEnum(Enum):
    @classmethod
    def choices(cls) -> Iterable[tuple[Any, str]]:
        return tuple((i.value, i.name) for i in cls)
