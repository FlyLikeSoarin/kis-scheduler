from typing import Any, Optional

from pydantic import BaseModel, UUID4, validator

from app.utils.typing import ChoicesEnum

from .helpers import ResourceData


class NodeStatus(str, ChoicesEnum):
    ACTIVE = 'active'
    FAILED = 'failed'
    DELETED = 'deleted'


class Node(BaseModel):
    id: UUID4 = None
    status: NodeStatus = NodeStatus.ACTIVE

    node_resources: Optional[ResourceData] = None
    available_resources: Optional[ResourceData] = None
    instance_ids: Optional[list[UUID4]] = None

    _was_updated: Optional[bool] = None

    @validator('node_resources')
    def validate_node_resources(cls, value: Optional[ResourceData], values: dict[str, Any]) -> Optional[ResourceData]:
        """Not deleted nodes must have a complete node_resources"""
        if values['status'] in (NodeStatus.ACTIVE, NodeStatus.FAILED) and value and value.is_complete():
            return value
        elif values['status'] == NodeStatus.DELETED:
            return None
        raise ValueError(
            'Resources of not deleted node must be complete' if value else 'Resources of deleted node must be None'
        )

    class Config:
        underscore_attrs_are_private = True
