import factory
from pydantic import ByteSize

from app.models import NodeModel, ServiceInstanceModel, ServiceModel
from app.schemas.nodes import NodeStatus
from app.schemas.services import (
    ExecutionStatus,
    DEFAULT_PRIORITY,
    ResourceStatus,
    ServiceInstanceStatus,
    ServiceStatus,
    ServiceType,
)


class BaseModelFactory(factory.Factory):
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class.create(**kwargs)


class NodeFactory(BaseModelFactory):
    id = factory.Faker("uuid4")
    status = NodeStatus.ACTIVE.value

    cpu_cores = 8.0
    ram = ByteSize.validate("32GiB")
    disk = ByteSize.validate("1TiB")

    class Meta:
        model = NodeModel


class ServiceFactory(BaseModelFactory):
    id = factory.Faker("uuid4")
    executable = factory.Faker("uuid4")
    status = ServiceStatus.ACTIVE.value
    type = ServiceType.STATELESS.value
    priority = DEFAULT_PRIORITY

    cpu_cores_limit = 1.0
    ram_limit = ByteSize.validate("1GiB")
    disk_limit = ByteSize.validate("10GiB")

    cpu_cores_floor = 1.0
    ram_floor = ByteSize.validate("1GiB")
    disk_floor = ByteSize.validate("10GiB")

    class Meta:
        model = ServiceModel


class ServiceInstanceFactory(BaseModelFactory):
    id = factory.Faker("uuid4")
    executable = factory.Faker("uuid4")
    status = ServiceInstanceStatus.PLACED.value
    execution_status = ExecutionStatus.UNKNOWN.value
    resource_status = ResourceStatus.OK.value

    cpu_cores = 1.0
    ram = ByteSize.validate("1GiB")
    disk = ByteSize.validate("10GiB")

    service = None
    host_node = None

    class Meta:
        model = ServiceInstanceModel
