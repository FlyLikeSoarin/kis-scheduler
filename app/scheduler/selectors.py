from typing import Callable, Optional

from app.schemas.helpers import ResourceData
from app.schemas.nodes import Node
from app.schemas.services import Service, ServiceInstance, ServiceType


SelectorType = Callable[[Service, Service], bool]

type_bonuses = {
    ServiceType.STATELESS: 0,
    ServiceType.FRAGILE: 100,
    ServiceType.STATEFUL: 200,
}


def any_with_lower_priority(requester: Service, target: Service) -> bool:
    return requester.priority > target.priority


def same_or_lower_type_with_lower_priority(requester: Service, target: Service) -> bool:
    return (requester.priority + type_bonuses[requester.type]) > (target.priority + type_bonuses[target.type])