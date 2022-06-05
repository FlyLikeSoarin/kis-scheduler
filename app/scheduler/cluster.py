from copy import deepcopy
from functools import partial
from typing import Iterable, Optional

from funcy import lfilter, lpluck_attr, pluck_attr, project
from pydantic import UUID4

from app.models import NodeModel, ServiceInstanceModel, ServiceModel
from app.schemas.helpers import ResourceData
from app.schemas.monitoring import SchedulerMetrics, TrackedAction, TrackedObjects
from app.schemas.nodes import Node, NodeStatus
from app.schemas.services import ExecutionStatus, ResourceStatus, Service, ServiceInstance, ServiceInstanceStatus, ServiceType
from app.utils.exceptions import EvictionError, SchedulingError

from .selectors import SelectorType


class ClusterState:
    def __init__(self):
        self.nodes: list[Node] = []
        self.services: list[Service] = []
        self.service_instances: list[ServiceInstance] = []

        self.ids_to_nodes_mapping: dict[UUID4, Node] = {}
        self.ids_to_services_mapping: dict[UUID4, Service] = {}
        self.ids_to_service_instances_mapping: dict[UUID4, ServiceInstance] = {}

        self.metrics = SchedulerMetrics()

        self._load_state()

    def _load_state(self):
        """Load state from persistent storage. Order is important"""
        self._load_service_instances()
        self._load_services()
        self._load_nodes()

    def _load_service_instances(self):
        """Load service instances, created ids to objects mapping"""
        self.service_instances: list[ServiceInstance] = ServiceInstanceModel.retrieve_schemas()
        self.ids_to_service_instances_mapping: dict[UUID4, ServiceInstance] = {
            obj.id: obj for obj in self.service_instances
        }

    def _load_services(self):
        """Load services, created ids to objects mapping, set backrefs"""
        self.services: list[Service] = ServiceModel.retrieve_schemas()
        self.ids_to_services_mapping: dict[UUID4, Service] = {obj.id: obj for obj in self.services}

        # Setting backrefs: for each service set instance_id to its instance
        for instance in self.service_instances:
            service = self.ids_to_services_mapping.get(instance.service_id, None)
            if service:
                service.instance_id = instance.id

    def _load_nodes(self):
        """Load services, created ids to objects mapping, set backref_ids"""
        self.nodes: list[Node] = NodeModel.retrieve_schemas()
        self.ids_to_nodes_mapping: dict[UUID4, Node] = {obj.id: obj for obj in self.nodes}

        # For each node set instance_ids to empty list
        for node in self.nodes:
            node.instance_ids = []

        # Setting backrefs: for each node set instance_ids to its instances
        for instance in self.service_instances:
            node = self.ids_to_nodes_mapping.get(instance.node_id, None)
            if node:
                node.instance_ids.append(instance.id)

    def commit(self):
        self.commit_nodes()
        self.commit_services()
        self.commit_instances()

    def commit_nodes(self):
        for node in self.nodes:
            NodeModel.synchronize_schema(node)

    def commit_services(self):
        for service in self.services:
            ServiceModel.synchronize_schema(service)

    def commit_instances(self):
        for instance in self.service_instances:
            ServiceInstanceModel.synchronize_schema(instance)

    def get_nodes_by_ids(self, ids: Iterable[UUID4]) -> Iterable[Node]:
        return project(self.ids_to_nodes_mapping, ids).values()

    def get_services_by_ids(self, ids: Iterable[UUID4]) -> Iterable[Service]:
        return project(self.ids_to_services_mapping, ids).values()

    def get_service_instances_by_ids(self, ids: Iterable[UUID4]) -> Iterable[ServiceInstance]:
        return project(self.ids_to_service_instances_mapping, ids).values()

    def get_node_instances(self, node) -> Iterable[ServiceInstance]:
        return self.get_service_instances_by_ids(node.instance_ids)

    def get_node_services(self, node) -> Iterable[Service]:
        return self.get_services_by_ids(pluck_attr('service_id', self.get_node_instances(node)))

    def finalize_metrics(self) -> SchedulerMetrics:
        self.metrics.increase_counter(TrackedObjects.NODE, len(self.nodes))
        self.metrics.increase_counter(TrackedObjects.SERVICE, len(self.service_instances))

        total, available = ResourceData(), ResourceData()
        for node in self.nodes:
            total += node.node_resources
            available += node.available_resources

        self.metrics.total_cluster_resources = total
        self.metrics.utilized_cluster_resources = total - available
        self.metrics.calculate_utilization()

        return self.metrics

    def calculate_available_resources(self):
        """For each node available resources is calculated (or set to None if error occurred)"""

        for node in self.nodes:
            instances = self.get_service_instances_by_ids(node.instance_ids)
            occupied_resources = ResourceData()

            for occupied_by_instance_resources in lpluck_attr("allocated_resources", instances):
                occupied_resources += occupied_by_instance_resources

            try:
                node.available_resources = node.node_resources - occupied_resources
            except ValueError:
                raise SchedulingError("available_resource cannot be negative")

    def attempt_to_acquire_resources(
        self, node: Node, required_resources: ResourceData, for_service: Service, selector: SelectorType
    ) -> Optional[list[ServiceInstance]]:
        """
        Attempt to acquire requested resources from node.
        If service can acquire requested resources through eviction of some (maybe empty) set,
        then ids of "to be evicted" instances is returned.
        Otherwise, EvictionError is raised.
        """
        if (node.available_resources is None) or not node.available_resources.is_complete():
            raise ValueError("To attempt to acquire resources from node available_resources must be set and complete")

        if node.available_resources.fits(required_resources):
            return []

        evictable_services: list[Service] = lfilter(
            partial(selector, for_service), self.get_node_services(node)
        )

        evicted_instances: list[ServiceInstance] = []
        sum_ = deepcopy(node.available_resources)
        for counter, service in enumerate(evictable_services):
            instance = self.ids_to_service_instances_mapping[service.instance_id]
            evicted_instances.append(instance)
            sum_ += instance.allocated_resources

            if sum_.fits(required_resources):
                return evicted_instances

        return None

    def evict_instance(self, instance: ServiceInstance, node: Optional[Node] = None):
        """Evicts instance from node. Adjusts available resources."""
        self.metrics.increase_counter(TrackedAction.EVICTION, 1)
        if self.ids_to_services_mapping[instance.service_id].type == ServiceType.FRAGILE:
            self.metrics.increase_counter(TrackedAction.FRAGILE_EVICTION, 1)

        if not node:
            node = self.ids_to_nodes_mapping[instance.id]
        if node.available_resources is not None:
            node.available_resources += instance.allocated_resources
        node.instance_ids = [_id for _id in node.instance_ids if _id != instance.id]

        instance.allocated_resources = None
        instance.node_id = None
        instance.status = ServiceInstanceStatus.EVICTED
        instance.execution_status = None
        instance.resource_status = None
        instance._was_updated = True

    def place_instance(self, instance: ServiceInstance, node: Node, required_resources: ResourceData):
        """
        Places instance onto node. Adjusts available resources.
        If there is not enough resources to place instance raises SchedulingError.
        """
        if not node.available_resources.fits(required_resources):
            raise SchedulingError()
        try:  # If there is not enough resources to place instance raises SchedulingError
            node.available_resources -= required_resources
            self.metrics.increase_counter(TrackedAction.ALLOCATION, 1)
        except (ValueError, AttributeError) as exc:
            raise SchedulingError(exc)
        node.instance_ids.append(instance.id)

        instance.allocated_resources = required_resources
        instance.node_id = node.id
        instance.status = ServiceInstanceStatus.PLACED
        instance.execution_status = ExecutionStatus.UNKNOWN
        instance.resource_status = ResourceStatus.OK
        instance._was_updated = False

    def shrink_instance(self, instance: ServiceInstance, resource_limit: ResourceData, node: Optional[Node] = None):
        """Shrink instance.allocated_resources to comply with resource_limit. Raises SchedulingError if not possible."""
        new_allocated_resources = instance.allocated_resources.get_compliant(resource_limit)

        if new_allocated_resources == instance.allocated_resources:
            return

        if not Node:
            node = self.ids_to_nodes_mapping[instance.node_id]

        self.evict_instance(instance, node)
        self.place_instance(instance, node, new_allocated_resources)

    def active_nodes(self) -> Iterable[Node]:
        return (node for node in self.nodes if node.status == NodeStatus.ACTIVE)
