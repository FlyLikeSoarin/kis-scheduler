from fastapi import APIRouter

from app.schemas.events import NodeEvent, ServiceInstanceEvent
from app.schemas.responses import EventResponse

router = APIRouter(prefix='/api/events')


@router.post('/node/', response_model=EventResponse)
def on_node_event(event: NodeEvent):
    pass


@router.post('/service-instance/', response_model=EventResponse)
def on_service_instance_event(event: ServiceInstanceEvent):
    pass
