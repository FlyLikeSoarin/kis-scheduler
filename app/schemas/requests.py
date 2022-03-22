from typing import Optional

from pydantic import BaseModel, UUID4, validator

from .helpers import ResourceData
from .services import ServiceType


class CreateNodeRequest(BaseModel):
    node_resources: ResourceData

    @validator('node_resources')
    def validate_node_resources(cls, value):
        if not value.is_complete():
            raise ValueError('Resource data should be complete when creating a node')
        return value


class UpdateNodeRequest(BaseModel):
    id: UUID4 = ...
    node_resources: Optional[ResourceData]


class DeleteNodeRequest(BaseModel):
    id: UUID4 = ...


class CreateServiceRequest(BaseModel):
    resource_limit: ResourceData = ...
    type: ServiceType = ...


class UpdateServiceRequest(BaseModel):
    id: UUID4 = ...
    resource_limit: Optional[ResourceData]


class DeleteServiceRequest(BaseModel):
    id: UUID4 = ...


