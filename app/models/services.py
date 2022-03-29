from typing import Iterable, Optional
from uuid import uuid4

from funcy import first, lmap
from peewee import CharField, IntegerField, FloatField, ForeignKeyField

from app.database import BaseModel
from app.schemas.helpers import ResourceData
from app.schemas.services import (
    Service,
    ServiceInstance,
    ServiceInstanceStatus,
    ServiceStatus,
    ServiceType,
)

from .mixins import WithResourceDataMixin
from .nodes import NodeModel


class ServiceModel(BaseModel):
    status = CharField(max_length=20, choices=ServiceStatus.choices())
    type = CharField(max_length=20, choices=ServiceType.choices())

    cpu_cores = FloatField(null=True)
    ram = IntegerField(null=True)
    disk = IntegerField(null=True)

    @classmethod
    def synchronize_schema(cls, service: Service) -> 'ServiceModel':
        model = (cls.create if service.id is None else cls.update)(
            id=service.id or uuid4(),  # Move id generation to DB
            status=service.status,
            type=service.type,
            cpu_cores=service.resource_limit.cpu_cores if service.resource_limit else None,
            ram=service.resource_limit.ram if service.resource_limit else None,
            disk=service.resource_limit.disk if service.resource_limit else None,
        )
        if service.id is None:
            service.id = model.id
        return model

    @staticmethod
    def _to_schema(model: 'ServiceModel') -> Service:
        return Service(
            id=model.id,
            status=model.status,
            type=model.type,
            resource_limit=ResourceData(
                cpu_cores=model.cpu_cores,
                ram=model.ram,
                disk=model.disk,
            ),
        )

    @classmethod
    def retrieve_schema(cls, service_id: str) -> Service:
        service = first(cls.retrieve_schemas([service_id]))
        if service is None:
            raise ValueError('Not found')
        return service

    @classmethod
    def retrieve_schemas(cls, service_ids: Optional[Iterable[str]] = None) -> list[Service]:
        query = cls.select()
        if service_ids:
            query = query.where(cls.id.in_(service_ids))
        models = list(query.execute())
        return lmap(cls._to_schema, models)

    @property
    def service_instance(self) -> Optional['ServiceInstanceModel']:
        """Real backref is private to make this relation behave as one-to-one"""
        return first(self._service_instances)


class ServiceInstanceModel(BaseModel):
    status = CharField(max_length=20, choices=ServiceInstanceStatus.choices())
    service = ForeignKeyField(ServiceModel, backref='_service_instances', unique=True, null=True)
    host_node = ForeignKeyField(NodeModel, backref='service_instances', null=True)

    cpu_cores = FloatField(null=True)
    ram = IntegerField(null=True)
    disk = IntegerField(null=True)

    @classmethod
    def synchronize_schema(cls, service_instance: ServiceInstance) -> 'ServiceInstanceModel':
        model = (cls.create if service_instance.id is None else cls.update)(
            id=service_instance.id or uuid4(),  # Move id generation to DB
            status=service_instance.status,
            cpu_cores=service_instance.allocated_resources.cpu_cores if service_instance.allocated_resources else None,
            ram=service_instance.allocated_resources.ram if service_instance.allocated_resources else None,
            disk=service_instance.allocated_resources.disk if service_instance.allocated_resources else None,
            host_node_id=service_instance.node_id,
            service_id=service_instance.service_id,
        )
        if service_instance.id is None:
            service_instance.id = model.id
        return model

    @staticmethod
    def _to_schema(model: 'ServiceInstanceModel') -> ServiceInstance:
        return ServiceInstance(
            id=model.id,
            status=model.status,
            resource_limit=ResourceData(
                cpu_cores=model.cpu_cores,
                ram=model.ram,
                disk=model.disk,
            ),
            node_id=model.host_node_id,
            service_id=model.service_id,
        )

    @classmethod
    def retrieve_schema(cls, service_instance_id: str) -> ServiceInstance:
        service_instance = first(cls.retrieve_schemas([service_instance_id]))
        if service_instance is None:
            raise ValueError('Not found')
        return service_instance

    @classmethod
    def retrieve_schemas(cls, service_instance_ids: Optional[Iterable[str]] = None) -> list[ServiceInstance]:
        query = cls.select()
        if service_instance_ids:
            query = query.where(cls.id.in_(service_instance_ids))
        models = list(query.execute())
        return lmap(cls._to_schema, models)
