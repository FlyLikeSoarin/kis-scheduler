from typing import Optional

from pydantic import UUID4, BaseModel, validator

from .helpers import ResourceData
from .nodes import NodeStatus
from .services import ServiceInstanceStatus


class NodeEvent(BaseModel):
    node_id: UUID4 = ...
    updated_status: Optional[NodeStatus] = None

    @validator("updated_status")
    def validate_updated_status(cls, value):
        if value in (NodeStatus.FAILED, NodeStatus.ACTIVE):
            return value
        raise ValueError("Forbidden updated_status. Allowed values: FAILED, OPERATIONAL")


class ServiceInstanceEvent(BaseModel):
    instance_id: UUID4 = ...
    updated_status: Optional[ServiceInstanceStatus] = None

    @validator("updated_status")
    def validate_updated_status(cls, value):
        if value in (
            ServiceInstanceStatus.CRASH_LOOP,
            ServiceInstanceStatus.RUNNING,
            ServiceInstanceStatus.EXCEEDED_CPU,
            ServiceInstanceStatus.EXCEEDED_RAM,
            ServiceInstanceStatus.EXCEEDED_DISK,
        ):
            return value
        raise ValueError("Forbidden updated_status. Allowed values: CRASH_LOOP, RUNNING, EXCEEDED_*")
