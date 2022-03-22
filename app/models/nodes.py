from peewee import CharField

from app.database import BaseModel
from app.schemas.nodes import NodeStatus

from .mixins import WithResourceDataMixin


class Node(WithResourceDataMixin, BaseModel):
    status = CharField(max_length=20, choices=NodeStatus.choices())
