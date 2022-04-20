from typing import Optional

from pydantic import UUID4, BaseModel, validator

from .helpers import ResourceData
from .nodes import NodeStatus
from .services import ExecutionStatus, ResourceStatus


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
    execution_status: Optional[ExecutionStatus] = None
    resource_status: Optional[ResourceStatus] = None
