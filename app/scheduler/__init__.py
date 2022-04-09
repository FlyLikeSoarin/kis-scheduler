from app.database import db

from .cluster import ClusterState
from .steps import NodeUpdatesResolver, ServiceUpdatesResolver, ServiceInstanceUpdatesResolver


class Scheduler:
    @classmethod
    def run_scheduling(cls):
        # with db.atomic():
        state = ClusterState()
        state = NodeUpdatesResolver.run(state)
        state = ServiceUpdatesResolver.run(state)
        state = ServiceInstanceUpdatesResolver.run(state)
        state.commit()
