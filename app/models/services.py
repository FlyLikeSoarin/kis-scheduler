from uuid import uuid4

from peewee import BooleanField, CharField, FloatField, ForeignKeyField, IntegerField, UUIDField

from app.database import BaseModel
from app.schemas.helpers import ResourceData
from app.schemas.services import Service, ServiceInstance, ServiceInstanceStatus, ServiceStatus, ServiceType

from .mixins import SchemaRetrieversMixin
from .nodes import NodeModel


class ServiceModel(SchemaRetrieversMixin, BaseModel):
    executable = UUIDField()
    status = CharField(max_length=20, choices=ServiceStatus.choices())
    type = CharField(max_length=20, choices=ServiceType.choices())
    priority = IntegerField()

    cpu_cores_limit = FloatField(null=True)
    ram_limit = IntegerField(null=True)
    disk_limit = IntegerField(null=True)

    cpu_cores_floor = FloatField(null=True)
    ram_floor = IntegerField(null=True)
    disk_floor = IntegerField(null=True)

    was_updated = BooleanField(null=False, default=True)

    @classmethod
    def synchronize_schema(cls, service: Service):
        query_kwargs = {
            "executable": service.executable,
            "status": service.status,
            "type": service.type,
            "priority": service.priority,

            "cpu_cores_limit": service.resource_limit.cpu_cores if service.resource_limit else None,
            "ram_limit": service.resource_limit.ram if service.resource_limit else None,
            "disk_limit": service.resource_limit.disk if service.resource_limit else None,

            "cpu_cores_floor": service.resource_floor.cpu_cores if service.resource_floor else None,
            "ram_floor": service.resource_floor.ram if service.resource_floor else None,
            "disk_floor": service.resource_floor.disk if service.resource_floor else None,

            "was_updated": True,
        }
        if service.id is None:
            saved_model = cls.create(id=uuid4(), **query_kwargs)  # TODO: Move id generation to DB
            service.id = saved_model.id
        else:
            cls.update(**query_kwargs).where(cls.id == service.id).execute()

    @staticmethod
    def _to_schema(model: "ServiceModel") -> Service:
        schema = Service(
            id=model.id,
            executable=model.executable,
            status=model.status,
            type=model.type,
            priority=model.priority,
            resource_limit=ResourceData(
                cpu_cores=model.cpu_cores_limit,
                ram=model.ram_limit,
                disk=model.disk_limit,
            ),
            resource_floor=ResourceData(
                cpu_cores=model.cpu_cores_floor,
                ram=model.ram_floor,
                disk=model.disk_floor,
            ),
            instance_id=None,
        )
        schema._was_updated = model.was_updated
        return schema


class ServiceInstanceModel(SchemaRetrieversMixin, BaseModel):
    executable = UUIDField()
    status = CharField(max_length=20, choices=ServiceInstanceStatus.choices())
    execution_status = CharField(max_length=20, choices=ServiceStatus.choices(), null=True)
    resource_status = CharField(max_length=20, choices=ServiceStatus.choices(), null=True)

    service = ForeignKeyField(ServiceModel, backref="_service_instances", unique=True, null=True, lazy_load=False)
    host_node = ForeignKeyField(NodeModel, backref="service_instances", null=True, lazy_load=False)

    cpu_cores = FloatField(null=True)
    ram = IntegerField(null=True)
    disk = IntegerField(null=True)

    was_updated = BooleanField(null=False, default=True)

    @classmethod
    def synchronize_schema(cls, service_instance: ServiceInstance):
        query_kwargs = {
            "executable": service_instance.executable,
            "status": service_instance.status,
            "execution_status": service_instance.execution_status,
            "resource_status": service_instance.resource_status,

            "host_node_id": service_instance.node_id,
            "service_id": service_instance.service_id,

            "cpu_cores": (
                service_instance.allocated_resources.cpu_cores
                if service_instance.allocated_resources
                else None
            ),
            "ram": service_instance.allocated_resources.ram if service_instance.allocated_resources else None,
            "disk": service_instance.allocated_resources.disk if service_instance.allocated_resources else None,

            "was_updated": True,
        }
        if service_instance.id is None:
            saved_model = cls.create(id=uuid4(), **query_kwargs)  # TODO: Move id generation to DB
            service_instance.id = saved_model.id
        else:
            cls.update(**query_kwargs).where(cls.id == service_instance.id).execute()

    @staticmethod
    def _to_schema(model: "ServiceInstanceModel") -> ServiceInstance:
        if all((model.cpu_cores is None, model.ram is None, model.disk is None)):
            allocated_resources = None
        else:
            allocated_resources = ResourceData(
                cpu_cores=model.cpu_cores,
                ram=model.ram,
                disk=model.disk,
            )
        schema = ServiceInstance(
            id=model.id,
            executable=model.executable,
            status=model.status,
            execution_status=model.execution_status,
            resource_status=model.resource_status,

            allocated_resources=allocated_resources,

            node_id=model.host_node,
            service_id=model.service_id,
        )
        schema._was_updated = model.was_updated
        return schema
