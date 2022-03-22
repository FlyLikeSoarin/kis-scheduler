from pydantic import BaseModel

from .nodes import Node
from .services import Service


class BaseResponse(BaseModel):
    status: str = 'OK'


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
