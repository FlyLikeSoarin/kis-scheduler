from fastapi import APIRouter, HTTPException

from app.models import NodeModel, ServiceInstanceModel
from app.schemas.events import NodeEvent, ServiceInstanceEvent
from app.schemas.nodes import NodeStatus
from app.schemas.responses import EventResponse
from app.schemas.services import ServiceInstanceStatus

router = APIRouter(prefix="/api/events")


@router.post("/nodes/", response_model=EventResponse)
def on_node_event(event: NodeEvent):
    try:
        node = NodeModel.retrieve_schema(str(event.node_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if node.status == NodeStatus.DELETED:
        raise HTTPException(status_code=403, detail="Event for deleted nodes are not allowed")

    if event.updated_status is not None:
        node.status = event.updated_status

    NodeModel.synchronize_schema(node)
    return EventResponse(status="OK")


@router.post("/service-instances/", response_model=EventResponse)
def on_service_instance_event(event: ServiceInstanceEvent):
    try:
        service_instance = ServiceInstanceModel.retrieve_schema(str(event.instance_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if service_instance.status != ServiceInstanceStatus.PLACED:
        raise HTTPException(status_code=403, detail="Event for not PLACED service instances are forbidden")

    if event.execution_status is not None:
        service_instance.execution_status = event.execution_status
    if event.resource_status is not None:
        service_instance.resource_status = event.resource_status

    ServiceInstanceModel.synchronize_schema(service_instance)
    return EventResponse(status="OK")
