from enum import Enum


class ChoicesEnum(Enum):

    @classmethod
    def choices(cls):
        return tuple((i.name, i.value) for i in cls)