import math
from typing import Optional

from pydantic import BaseModel, ByteSize, Field, validator


class ResourceData(BaseModel):
    cpu_cores: Optional[float] = Field(None, ge=0.5)
    ram: Optional[ByteSize] = None
    disk: Optional[ByteSize] = None

    @validator('cpu_cores', pre=True)
    def validate_cpu_cores(cls, value):
        if value:
            return math.ceil(value * 10.) / 10.
        return None

    def is_complete(self):
        return not (self.cpu_cores is None or self.ram is None or self.disk is None)