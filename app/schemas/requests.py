from typing import Any, Optional

from pydantic import UUID4, BaseModel, validator

from .helpers import ResourceData
from .services import ServiceType


class CreateNodeRequest(BaseModel):
    node_resources: ResourceData

    @validator("node_resources")
    def validate_node_resources(cls, value: ResourceData) -> ResourceData:
        if not value.is_complete():
            raise ValueError("Resource data should be complete when creating a node")
        return value


class CreateServiceRequest(BaseModel):
    executable: UUID4 = ...
    type: ServiceType = ...
    priority: int = 99
    resource_limit: ResourceData = ...
    resource_floor: ResourceData = ...


class UpdateServiceRequest(BaseModel):
    executable: Optional[UUID4] = None
    priority: Optional[int] = None
    resource_limit: Optional[ResourceData] = None
    resource_floor: Optional[ResourceData] = None
