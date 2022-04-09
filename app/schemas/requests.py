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


class UpdateNodeRequest(BaseModel):
    node_resources: Optional[ResourceData]


class CreateServiceRequest(BaseModel):
    resource_limit: ResourceData = ...
    type: ServiceType = ...


class UpdateServiceRequest(BaseModel):
    resource_limit: Optional[ResourceData]
