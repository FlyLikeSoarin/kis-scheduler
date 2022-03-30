from typing import Iterable, Optional
from uuid import uuid4

from funcy import first, lmap
from peewee import BooleanField, CharField, IntegerField, FloatField

from app.database import BaseModel
from app.schemas.nodes import Node, NodeStatus
from app.schemas.helpers import ResourceData


class NodeModel(BaseModel):
    status = CharField(max_length=20, choices=NodeStatus.choices())

    cpu_cores = FloatField(null=True)
    ram = IntegerField(null=True)
    disk = IntegerField(null=True)

    was_updated = BooleanField(null=False, default=True)

    @classmethod
    def synchronize_schema(cls, node: Node) -> 'NodeModel':
        model = (cls.create if node.id is None else cls.update)(
            id=node.id or uuid4(),  # Move id generation to DB
            status=node.status,
            cpu_cores=node.node_resources.cpu_cores if node.node_resources else None,
            ram=node.node_resources.ram if node.node_resources else None,
            disk=node.node_resources.disk if node.node_resources else None,
            was_updated=True,
        )
        if node.id is None:
            node.id = model.id
        return model

    @staticmethod
    def _to_schema(model: 'NodeModel') -> Node:
        return Node(
            id=model.id,
            status=model.status,
            node_resources=ResourceData(
                cpu_cores=model.cpu_cores,
                ram=model.ram,
                disk=model.disk,
            ),
        )

    @classmethod
    def retrieve_schema(cls, node_id: str) -> Node:
        node = first(cls.retrieve_schemas([node_id]))
        if node is None:
            raise ValueError('Not found')
        return node

    @classmethod
    def retrieve_schemas(cls, node_ids: Optional[Iterable[str]] = None) -> list[Node]:
        query = cls.select()
        if node_ids:
            query = query.where(cls.id.in_(node_ids))
        models = list(query.execute())
        return lmap(cls._to_schema, models)
