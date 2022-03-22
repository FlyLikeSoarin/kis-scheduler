from peewee import CharField

from app.database import BaseModel
from app.schemas.services import ServiceInstanceStatus, ServiceStatus, ServiceType

from .mixins import WithResourceDataMixin


class Service(WithResourceDataMixin, BaseModel):
    status = CharField(max_length=20, choices=ServiceStatus.choices())
    type = CharField(max_length=20, choices=ServiceType.choices())


class ServiceInstance(WithResourceDataMixin, BaseModel):
    status = CharField(max_length=20, choices=ServiceInstanceStatus.choices())
