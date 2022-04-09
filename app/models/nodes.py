from typing import Iterable, Optional
from uuid import uuid4

from funcy import first, lmap
from peewee import BooleanField, CharField, FloatField, IntegerField

from app.database import BaseModel
from app.schemas.helpers import ResourceData
from app.schemas.nodes import Node, NodeStatus


class NodeModel(BaseModel):
    status = CharField(max_length=20, choices=NodeStatus.choices())

    cpu_cores = FloatField(null=True)
    ram = IntegerField(null=True)
    disk = IntegerField(null=True)

    was_updated = BooleanField(null=False, default=True)

    @classmethod
    def synchronize_schema(cls, node: Node):
        query_kwargs = {
            "status": node.status.value,
            "cpu_cores": node.node_resources.cpu_cores if node.node_resources else None,
            "ram": node.node_resources.ram if node.node_resources else None,
            "disk": node.node_resources.disk if node.node_resources else None,
            "was_updated": True,
        }
        if node.id is None:
            saved_model = cls.create(id=uuid4(), **query_kwargs)  # TODO: Move id generation to DB
            node.id = saved_model.id
        else:
            cls.update(**query_kwargs).where(cls.id == node.id).execute()

    @staticmethod
    def _to_schema(model: "NodeModel") -> Node:
        schema = Node(
            id=model.id,
            status=model.status,
            node_resources=ResourceData(
                cpu_cores=model.cpu_cores,
                ram=model.ram,
                disk=model.disk,
            ),
        )
        schema._was_updated = model.was_updated
        return schema

    @classmethod
    def retrieve_schema(cls, node_id: str) -> Node:
        node = first(cls.retrieve_schemas([node_id]))
        if node is None:
            raise ValueError("Not found")
        return node

    @classmethod
    def retrieve_schemas(cls, node_ids: Optional[Iterable[str]] = None) -> list[Node]:
        if node_ids:
            return cls.retrieve_schemas_where(cls.id.in_(node_ids))
        return cls.retrieve_schemas_where()

    @classmethod
    def retrieve_schemas_where(cls, *where_params) -> list[Node]:
        query = cls.select()
        if where_params:
            query = query.where(*where_params)
        models = list(query.execute())
        return lmap(cls._to_schema, models)
