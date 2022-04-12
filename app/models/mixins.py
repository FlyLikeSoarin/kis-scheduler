from typing import Iterable, Optional

from funcy import first, lmap
from peewee import FloatField, IntegerField, Model
from pydantic import BaseModel


class ResourceDataMixin(Model):
    cpu_cores = FloatField(null=True)
    ram = IntegerField(null=True)
    disk = IntegerField(null=True)


class SchemaRetrieversMixin:
    @classmethod
    def retrieve_schema(cls, obj_id: str) -> BaseModel:
        """
        Retrieve schema with by id.
        Class with this mixin must be a model to use this method.
        """
        scheduler_log = first(cls.retrieve_schemas([obj_id]))
        if scheduler_log is None:
            raise ValueError("Not found")
        return scheduler_log

    @classmethod
    def retrieve_schemas(cls, obj_ids: Optional[Iterable[str]] = None) -> list[BaseModel]:
        """
        Retrieve schemas with ids listed in log_ids.
        Class with this mixin must be a model to use this method.
        """

        if obj_ids:
            return cls.retrieve_schemas_where(cls.id.in_(obj_ids))  # type: ignore
        return cls.retrieve_schemas_where()

    @classmethod
    def retrieve_schemas_where(cls, *where_params) -> list[BaseModel]:
        """
        Retrieve schemas with any filtering.
        Class with this mixin must be a model with a valid _schema method to use this method.
        """
        query = cls.select()  # type: ignore
        if where_params:
            query = query.where(*where_params)
        models = list(query.execute())
        return lmap(cls._to_schema, models)  # type: ignore
