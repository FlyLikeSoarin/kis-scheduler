from typing import Optional, Union

from pydantic import BaseModel, UUID4, validator

from app.utils.typing import ChoicesEnum

from .helpers import ResourceData
from .services import ServiceInstance

ListOfInstancesOrIds = Union[list[ServiceInstance, UUID4]]


class NodeStatus(str, ChoicesEnum):
    OPERATIONAL = 'operational'
    UNKNOWN = 'unknown'
    DELETED = 'deleted'


class Node(BaseModel):
    id: UUID4 = ...
    node_id: Optional[UUID4] = None
    status: NodeStatus = NodeStatus.UNKNOWN
    node_resources: Optional[ResourceData] = None
    available_resources: Optional[ResourceData] = None
    instances: Optional[ListOfInstancesOrIds] = None

    @validator('allocated_resources')
    def validate_allocated_resources(cls, value, values):
        """Not deleted nodes must have a complete node_resources"""
        if values['status'] in (NodeStatus.OPERATIONAL, NodeStatus.UNKNOWN) and value.is_complete():
            return value
        elif values['status'] == NodeStatus.DELETED:
            return None
        raise ValueError('Allocated resources must be None or complete')
