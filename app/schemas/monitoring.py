from datetime import datetime, timedelta
from typing import Any, Optional, Union

from pydantic import UUID4, BaseModel, root_validator

from app.utils.typing import ChoicesEnum

from .helpers import ResourceData, resource_types


class TrackedAction(str, ChoicesEnum):
    EVICTION = "eviction"
    ALLOCATION = "allocation"


class TrackedObjects(str, ChoicesEnum):
    NODE = "node"
    SERVICE = "service"
    EVICTED = "evicted"


class SchedulerMetrics(BaseModel):
    duration: Optional[timedelta] = None

    total_cluster_resources: Optional[ResourceData] = None
    utilized_cluster_resources: Optional[ResourceData] = None
    utilization: dict = {}

    actions_counter: dict[TrackedAction, int] = {}
    objects_counter: dict[TrackedObjects, int] = {}

    @root_validator()
    def utilized_fits_in_total(cls, values: dict[str:Any]) -> dict[str:Any]:
        total, utilized = values.get("total_cluster_resources", None), values.get("utilized_cluster_resources", None)
        if total and utilized:
            if not total.fits(utilized):
                raise ValueError("Utilized must fit into total")
        return values

    def calculate_utilization(self):
        for resource_type in resource_types:
            total = getattr(self.total_cluster_resources, resource_type)
            utilized = getattr(self.utilized_cluster_resources, resource_type)
            if (total is not None) and (utilized is not None):
                self.utilization[resource_type] = utilized / total

    def increase_counter(self, on: Union[TrackedAction, TrackedObjects], by: int):
        if isinstance(on, TrackedAction):
            to = self.actions_counter
        else:
            to = self.objects_counter
        to[on] = (to[on] + by) if (on in to) else 0


class SchedulerLog(BaseModel):
    id: UUID4 = None
    metrics: SchedulerMetrics
    timestamp: datetime = None

    def is_persisted(self) -> bool:
        return bool(self.id) and bool(self.timestamp)

    class Config:
        underscore_attrs_are_private = True
