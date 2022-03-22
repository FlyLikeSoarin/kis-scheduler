from typing import Optional

from pydantic import BaseModel, UUID4

from .nodes import NodeStatus
from .services import ServiceInstanceStatus


class ServiceInstanceEvent(BaseModel):
    instance_id: UUID4 = ...
    updated_status: Optional[ServiceInstanceStatus] = None


class NodeEvent(BaseModel):
    node_id: UUID4 = ...
    updated_status: Optional[NodeStatus] = None
