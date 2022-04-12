from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import UUID4

from app.models import SchedulerLogModel
from app.scheduler.cluster import ClusterState
from app.schemas.responses import ClusterStateResponse, MetricsResponse

router = APIRouter(prefix="/api/monitoring")


@router.get("/state/", response_model=ClusterStateResponse)
def retrieve_cluster_state():
    state = ClusterState()
    return ClusterStateResponse(
        status="OK",
        services=state.services,
        service_instances=state.service_instances,
        nodes=state.nodes,
    )


@router.get("/metrics/", response_model=MetricsResponse)
def retrieve_metrics(
    from_datetime: Optional[datetime] = Query(None, alias="from"),
    duration: Optional[timedelta] = None,
):
    if from_datetime:
        logs = SchedulerLogModel.retrieve_schemas_where(SchedulerLogModel.timestamp > from_datetime)
    elif duration:
        logs = SchedulerLogModel.retrieve_schemas_where(SchedulerLogModel.timestamp > (datetime.now() - duration))
    else:
        logs = SchedulerLogModel.retrieve_schemas()
    return MetricsResponse(
        status="OK",
        data=logs,
    )
