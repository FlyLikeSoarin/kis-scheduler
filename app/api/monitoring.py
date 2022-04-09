from fastapi import APIRouter

from app.models import NodeModel, ServiceModel, ServiceInstanceModel
from app.scheduler.cluster import ClusterState
from app.schemas.responses import ClusterStateResponse

router = APIRouter(prefix='/api/monitoring')


@router.get('/state/', response_model=ClusterStateResponse)
def retrieve_cluster_state():
    state = ClusterState()
    return ClusterStateResponse(
        status='OK',
        services=state.services,
        service_instances=state.service_instances,
        nodes=state.nodes,
    )
