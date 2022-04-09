import math
from copy import deepcopy
from typing import Any, Optional

from funcy import lmap, lpluck_attr
from pydantic import BaseModel, ByteSize, Field, validator

resource_types = ("cpu_cores", "ram", "disk")

increase_resource_step_kwargs = {
    "cpu_cores": 1.0,
    "ram": ByteSize.validate("1GiB"),  # 1GiB
    "disk": ByteSize.validate("10GiB"),  # 10GiB
}


class ResourceData(BaseModel):
    cpu_cores: Optional[float] = Field(None, ge=0.0)
    ram: Optional[ByteSize] = None
    disk: Optional[ByteSize] = None

    @validator("cpu_cores", pre=True)
    def validate_cpu_cores(cls, value: Any) -> Optional[float]:
        if isinstance(value, (float, int)):
            return math.ceil(value * 10) / 10.0
        return None

    def is_complete(self) -> bool:
        return not (self.cpu_cores is None or self.ram is None or self.disk is None)

    def __iadd__(self, other: "ResourceData") -> "ResourceData":
        for resource_type in resource_types:
            setattr(self, resource_type, (getattr(self, resource_type) or 0) + (getattr(other, resource_type) or 0))
        return self

    def __add__(self, other: "ResourceData") -> "ResourceData":
        self_copy = deepcopy(self)
        self_copy += other
        return self_copy

    def __isub__(self, other: "ResourceData") -> "ResourceData":
        resource_data_kwargs = {
            resource_type: (getattr(self, resource_type) or 0) - (getattr(other, resource_type) or 0)
            for resource_type in resource_types
        }
        if any(lmap(lambda x: x < 0, resource_data_kwargs.values())):
            raise ValueError()
        for resource_type in resource_types:
            setattr(self, resource_type, resource_data_kwargs[resource_type])
        return self

    def __sub__(self, other: "ResourceData") -> "ResourceData":
        self_copy = deepcopy(self)
        self_copy -= other
        return self_copy

    def __eq__(self, other):
        return all(getattr(self, resource_type) == getattr(other, resource_type) for resource_type in resource_types)

    def fits(self, other: "ResourceData") -> bool:
        return all(
            (
                (getattr(self, resource_type) is None)
                or (getattr(self, resource_type) >= getattr(other, resource_type, 0))
            )
            for resource_type in resource_types
        )

    def get_compliant(self, resource_limit: "ResourceData") -> "ResourceData":
        def _get_compliant_resource(resource_type):
            allocated_value, limit_value = lpluck_attr(resource_type, (self, resource_limit))
            return min(allocated_value, limit_value)

        resource_data_kwargs = {
            resource_type: _get_compliant_resource(resource_type) for resource_type in resource_types
        }
        return ResourceData(**resource_data_kwargs)


base_allocated_resources = ResourceData(**increase_resource_step_kwargs)
