from typing import Optional

from pydantic import BaseModel, UUID4, validator

from app.utils.typing import ChoicesEnum

from .helpers import ResourceData


class ServiceType(str, ChoicesEnum):
    STATELESS = 'stateless'
    FRAGILE = 'fragile'
    STATEFUL = 'stateful'


class ServiceStatus(str, ChoicesEnum):
    ACTIVE = 'active'
    DELETED = 'deleted'


class ServiceInstanceStatus(str, ChoicesEnum):
    CREATED = 'created'
    RUNNING = 'running'
    CRASH_LOOP = 'crash_loop'
    EVICTED = 'evicted'
    DELETED = 'deleted'


class ServiceInstance(BaseModel):
    id: UUID4 = ...
    node_id: Optional[UUID4] = None
    status: ServiceInstanceStatus = ServiceInstanceStatus.CREATED
    allocated_resources: Optional[ResourceData] = None

    @validator('allocated_resources')
    def validate_allocated_resources(cls, value):
        if value is None or value.is_complete():
            return value
        raise ValueError('Allocated resources must be None or complete')


class Service(BaseModel):
    id: UUID4 = ...
    status: ServiceStatus = ServiceStatus.ACTIVE
    type: ServiceType = ...
    resource_limit: ResourceData = ...
    instance: Optional[ServiceInstance] = None

