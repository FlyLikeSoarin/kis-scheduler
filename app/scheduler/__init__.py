from contextlib import contextmanager
from datetime import timedelta
from time import perf_counter

from app.database import db
from app.models import SchedulerLogModel
from app.schemas.monitoring import SchedulerLog

from .cluster import ClusterState
from .steps import NodeUpdatesResolver, ServiceInstanceUpdatesResolver, ServiceUpdatesResolver


@contextmanager
def catch_time() -> float:
    start = perf_counter()
    yield lambda: perf_counter() - start


class Scheduler:
    @classmethod
    def run_scheduling(cls):
        with db.atomic(), catch_time() as get_seconds:
            state = ClusterState()
            state = NodeUpdatesResolver.run(state)
            state = ServiceUpdatesResolver.run(state)
            state = ServiceInstanceUpdatesResolver.run(state)
            state.commit()

        state.metrics.duration = timedelta(seconds=get_seconds())
        SchedulerLogModel.persist_schema(SchedulerLog(metrics=state.metrics))
