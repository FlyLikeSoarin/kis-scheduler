from typing import Iterable, Optional
from uuid import uuid4

from funcy import first, lmap
from peewee import (BooleanField, CharField, FloatField, ForeignKeyField,
                    IntegerField)

from app.database import BaseModel
from app.schemas.helpers import ResourceData
from app.schemas.services import (Service, ServiceInstance,
                                  ServiceInstanceStatus, ServiceStatus,
                                  ServiceType)

from .nodes import NodeModel


class ServiceModel(BaseModel):
    status = CharField(max_length=20, choices=ServiceStatus.choices())
    type = CharField(max_length=20, choices=ServiceType.choices())

    cpu_cores = FloatField(null=True)
    ram = IntegerField(null=True)
    disk = IntegerField(null=True)

    was_updated = BooleanField(null=False, default=True)

    @classmethod
    def synchronize_schema(cls, service: Service):

        query_kwargs = {
            "status": service.status,
            "type": service.type,
            "cpu_cores": service.resource_limit.cpu_cores if service.resource_limit else None,
            "ram": service.resource_limit.ram if service.resource_limit else None,
            "disk": service.resource_limit.disk if service.resource_limit else None,
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
            status=model.status,
            type=model.type,
            resource_limit=ResourceData(
                cpu_cores=model.cpu_cores,
                ram=model.ram,
                disk=model.disk,
            ),
            instance_id=None,
        )
        schema._was_updated = model.was_updated
        return schema

    @classmethod
    def retrieve_schema(cls, service_id: str) -> Service:
        service = first(cls.retrieve_schemas([service_id]))
        if service is None:
            raise ValueError("Not found")
        return service

    @classmethod
    def retrieve_schemas(cls, service_ids: Optional[Iterable[str]] = None) -> list[Service]:
        if service_ids:
            return cls.retrieve_schemas_where(cls.id.in_(service_ids))
        return cls.retrieve_schemas_where()

    @classmethod
    def retrieve_schemas_where(cls, *where_params) -> list[Service]:
        query = cls.select()
        if where_params:
            query = query.where(*where_params)
        models = list(query.execute())
        return lmap(cls._to_schema, models)


class ServiceInstanceModel(BaseModel):
    status = CharField(max_length=20, choices=ServiceInstanceStatus.choices())
    service = ForeignKeyField(ServiceModel, backref="_service_instances", unique=True, null=True, lazy_load=False)
    host_node = ForeignKeyField(NodeModel, backref="service_instances", null=True, lazy_load=False)

    cpu_cores = FloatField(null=True)
    ram = IntegerField(null=True)
    disk = IntegerField(null=True)

    was_updated = BooleanField(null=False, default=True)

    @classmethod
    def synchronize_schema(cls, service_instance: ServiceInstance):
        query_kwargs = {
            "status": service_instance.status,
            "cpu_cores": service_instance.allocated_resources.cpu_cores
            if service_instance.allocated_resources
            else None,
            "ram": service_instance.allocated_resources.ram if service_instance.allocated_resources else None,
            "disk": service_instance.allocated_resources.disk if service_instance.allocated_resources else None,
            "host_node_id": service_instance.node_id,
            "service_id": service_instance.service_id,
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
            status=model.status,
            allocated_resources=allocated_resources,
            node_id=model.host_node,
            service_id=model.service_id,
        )
        schema._was_updated = model.was_updated
        return schema

    @classmethod
    def retrieve_schema(cls, service_instance_id: str) -> ServiceInstance:
        service_instance = first(cls.retrieve_schemas([service_instance_id]))
        if service_instance is None:
            raise ValueError("Not found")
        return service_instance

    @classmethod
    def retrieve_schemas(cls, service_instance_ids: Optional[Iterable[str]] = None) -> list[ServiceInstance]:
        if service_instance_ids:
            return cls.retrieve_schemas_where(cls.id.in_(service_instance_ids))
        return cls.retrieve_schemas_where()

    @classmethod
    def retrieve_schemas_where(cls, *where_params) -> list[ServiceInstance]:
        query = cls.select()
        if where_params:
            query = query.where(*where_params)
        models = list(query.execute())
        return lmap(cls._to_schema, models)
