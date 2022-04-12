import json
from datetime import datetime
from uuid import uuid4

from peewee import DateTimeField, TextField

from app.database import BaseModel
from app.schemas.monitoring import SchedulerLog, SchedulerMetrics

from .mixins import SchemaRetrieversMixin


class SchedulerLogModel(SchemaRetrieversMixin, BaseModel):
    metrics = TextField(default="{}")
    timestamp = DateTimeField(default=datetime.now)

    @classmethod
    def persist_schema(cls, scheduler_log: SchedulerLog):
        saved_model = cls.create(id=uuid4(), metrics=scheduler_log.metrics.json())

        scheduler_log.id = saved_model.id
        scheduler_log.timestamp = saved_model.timestamp

    @staticmethod
    def _to_schema(model: "SchedulerLogModel") -> SchedulerLog:
        schema = SchedulerLog(
            id=model.id,
            metrics=SchedulerMetrics.parse_raw(model.metrics),  # type: ignore
            timestamp=model.timestamp,
        )
        return schema
