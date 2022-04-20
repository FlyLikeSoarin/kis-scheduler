from typing import Any, Optional

from pydantic import UUID4, BaseModel, Field, validator

from app.utils.typing import ChoicesEnum

from .helpers import ResourceData

DEFAULT_PRIORITY = 99


class ServiceType(str, ChoicesEnum):
    STATELESS = "stateless"
    FRAGILE = "fragile"
    STATEFUL = "stateful"


class ServiceStatus(str, ChoicesEnum):
    ACTIVE = "active"
    DELETED = "deleted"


class ServiceInstanceStatus(str, ChoicesEnum):
    PLACED = 'placed'
    EVICTED = "evicted"
    DELETED = "deleted"


class ExecutionStatus(str, ChoicesEnum):
    UNKNOWN = 'unknown'
    RUNNING = 'running'
    CRASH_LOOP = 'crash_loop'


class ResourceStatus(str, ChoicesEnum):
    OK = 'ok'
    CONSTRAINT_BY_CPU = 'cpu_cores'
    CONSTRAINT_BY_RAM = 'ram'
    CONSTRAINT_BY_DISK = 'disk'


class ServiceInstance(BaseModel):
    id: UUID4 = None
    executable: UUID4 = None
    status: ServiceInstanceStatus = ServiceInstanceStatus.EVICTED
    execution_status: Optional[ExecutionStatus] = ExecutionStatus.UNKNOWN
    resource_status: Optional[ResourceStatus] = ResourceStatus.OK
    allocated_resources: Optional[ResourceData] = None
    node_id: Optional[UUID4] = None
    service_id: Optional[UUID4] = None

    _was_updated: Optional[bool] = None

    @validator("allocated_resources")
    def validate_allocated_resources(cls, value: Any) -> Optional[ResourceData]:
        if value is None or value.is_complete():
            return value
        raise ValueError("Allocated resources must be None or complete")

    @validator("execution_status")
    def validate_execution_status(cls, value: Any, values: dict[str, Any]) -> Optional[ExecutionStatus]:
        return cls._check_additional_status_compatibility(value, values['status'], 'Execution')

    @validator("resource_status")
    def validate_resource_status(cls, value: Any, values: dict[str, Any]) -> Optional[ExecutionStatus]:
        return cls._check_additional_status_compatibility(value, values['status'], 'Resource')

    @staticmethod
    def _check_additional_status_compatibility(value: Any, status: ServiceInstanceStatus, name: str):
        if value is None and status != ServiceInstanceStatus.PLACED:
            return value
        if value is not None and status == ServiceInstanceStatus.PLACED:
            return value
        raise ValueError(f"{name}_status must be set only on PLACED instances")

    class Config:
        underscore_attrs_are_private = True


class Service(BaseModel):
    id: UUID4 = None
    executable: UUID4 = None
    status: ServiceStatus = ServiceStatus.ACTIVE
    type: ServiceType = ...
    priority: int = Field(DEFAULT_PRIORITY, ge=0, lt=100)
    resource_limit: Optional[ResourceData] = ...
    resource_floor: Optional[ResourceData] = ...
    instance_id: Optional[UUID4] = None

    _was_updated: Optional[bool] = None

    @validator("resource_limit")
    def validate_resource_limit(cls, value: Any, values: dict[str, Any]) -> Optional[ResourceData]:
        return cls._check_resource_compatibility(value, values["status"], 'limit')

    @validator("resource_floor")
    def validate_resource_floor(cls, value: Any, values: dict[str, Any]) -> Optional[ResourceData]:
        return cls._check_resource_compatibility(value, values["status"], 'floor')

    @staticmethod
    def _check_resource_compatibility(value: Any, status: ServiceStatus, name: str):
        if value is None and status == ServiceStatus.DELETED:
            return value
        if value is not None and status == ServiceStatus.ACTIVE:
            return value
        raise ValueError(f"Resource_{name} must be set only on ACTIVE services")

    def has_type_priority_over(self, other: "Service") -> bool:
        return other.type in {
            ServiceType.STATELESS: (),
            ServiceType.FRAGILE: (ServiceType.STATELESS,),
            ServiceType.STATEFUL: (ServiceType.FRAGILE, ServiceType.STATELESS),
        }.get(self.type, ())

    class Config:
        underscore_attrs_are_private = True
