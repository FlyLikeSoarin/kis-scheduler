from typing import Any, Optional

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
    REACHED_RESOURCE_LIMIT = 'reached_resource_limit'
    EVICTED = 'evicted'
    DELETED = 'deleted'


class ServiceInstance(BaseModel):
    id: UUID4 = None
    node_id: Optional[UUID4] = None
    service_id: Optional[UUID4] = None
    status: ServiceInstanceStatus = ServiceInstanceStatus.CREATED
    allocated_resources: Optional[ResourceData] = None

    @validator('allocated_resources')
    def validate_allocated_resources(cls, value: Any) -> Optional[ResourceData]:
        if value is None or value.is_complete():
            return value
        raise ValueError('Allocated resources must be None or complete')


class Service(BaseModel):
    id: UUID4 = None
    status: ServiceStatus = ServiceStatus.ACTIVE
    type: ServiceType = ...
    resource_limit: Optional[ResourceData] = ...
    instance: Optional[ServiceInstance] = None

    @validator('resource_limit')
    def validate_resource_limit(cls, value: Any, values: dict[str, Any]) -> Optional[ResourceData]:
        if value is None and values['status'] == ServiceStatus.DELETED:
            return value
        if value is not None and values['status'] == ServiceStatus.ACTIVE:
            return value
        raise ValueError('Allocated resources must be None or complete')

