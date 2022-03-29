from pydantic import BaseModel

from .nodes import Node
from .services import Service, ServiceInstance


class BaseResponse(BaseModel):
    status: str = ...


class EventResponse(BaseResponse):
    pass


class NodeResponse(BaseResponse):
    data: Node = ...


class NodeListResponse(BaseResponse):
    data: list[Node] = ...


class ServiceResponse(BaseResponse):
    data: Service = ...


class ServiceListResponse(BaseResponse):
    data: list[Service] = ...


class ClusterStateResponse(BaseResponse):
    services: list[Service] = ...
    service_instances: list[ServiceInstance] = ...
    nodes: list[Node] = ...
