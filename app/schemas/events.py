from typing import Optional

from pydantic import BaseModel, UUID4, validator

from .helpers import ResourceData
from .nodes import NodeStatus
from .services import ServiceInstanceStatus


class NodeEvent(BaseModel):
    node_id: UUID4 = ...
    updated_status: Optional[NodeStatus] = None

    @validator('updated_status')
    def validate_updated_status(cls, value):
        if value in (NodeStatus.UNKNOWN, NodeStatus.OPERATIONAL):
            return value
        raise ValueError('Forbidden updated_status. Allowed values: UNKNOWN, OPERATIONAL')


class ServiceInstanceEvent(BaseModel):
    instance_id: UUID4 = ...
    updated_status: Optional[ServiceInstanceStatus] = None

    @validator('updated_status')
    def validate_updated_status(cls, value):
        if value in (
            ServiceInstanceStatus.CRASH_LOOP,
            ServiceInstanceStatus.RUNNING,
            ServiceInstanceStatus.REACHED_RESOURCE_LIMIT,
        ):
            return value
        raise ValueError('Forbidden updated_status. Allowed values: CRASH_LOOP, RUNNING, REACHED_RESOURCE_LIMIT')
