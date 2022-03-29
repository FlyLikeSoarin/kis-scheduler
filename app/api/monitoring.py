from fastapi import APIRouter

from app.models import NodeModel, ServiceModel, ServiceInstanceModel
from app.schemas.responses import ClusterStateResponse

router = APIRouter(prefix='/api/monitoring')


@router.get('/state/', response_model=ClusterStateResponse)
def retrieve_cluster_state():
    return ClusterStateResponse(
        status='OK',
        services=ServiceModel.retrieve_schemas(),
        service_instances=ServiceInstanceModel.retrieve_schemas(),
        nodes=NodeModel.retrieve_schemas(),
    )
