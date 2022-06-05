from typing import Optional

from funcy import lfilter, lpluck_attr, pluck_attr
from pydantic import UUID4

from app.models import ServiceInstanceModel
from app.schemas.helpers import ResourceData, base_allocated_resources, increase_resource_step_kwargs, resource_types
from app.schemas.monitoring import TrackedObjects
from app.schemas.nodes import Node, NodeStatus
from app.schemas.services import ExecutionStatus, ResourceStatus, Service, ServiceInstance, ServiceInstanceStatus, ServiceStatus, ServiceType
from app.utils.exceptions import EvictionError, SchedulingError

from .cluster import ClusterState
from .selectors import any_with_lower_priority, same_or_lower_type_with_lower_priority


class NodeUpdatesResolver:
    @staticmethod
    def run(state: ClusterState) -> ClusterState:
        updated_nodes_ids: set[UUID4] = set(pluck_attr("id", filter(lambda obj: obj._was_updated, state.nodes)))

        state, updated_nodes_ids = NodeUpdatesResolver.evict_from_non_active_nodes(state, updated_nodes_ids)
        state, updated_nodes_ids = NodeUpdatesResolver.resolve_active_nodes(state, updated_nodes_ids)

        if len(updated_nodes_ids) != 0:
            raise SchedulingError("Not all updated nodes resolved")

        return state

    @staticmethod
    def evict_from_non_active_nodes(
        state: ClusterState, updated_nodes_ids: set[UUID4]
    ) -> tuple[ClusterState, set[UUID4]]:
        for node_id in list(updated_nodes_ids):
            node: Node = state.ids_to_nodes_mapping[node_id]

            if node.status not in (NodeStatus.FAILED, NodeStatus.DELETED):
                continue

            for instance_id in node.instance_ids:
                instance: ServiceInstance = state.ids_to_service_instances_mapping[instance_id]
                state.evict_instance(instance, node)

            node.instance_ids = []
            node._was_updated = False
            updated_nodes_ids.remove(node_id)

        return state, updated_nodes_ids

    @staticmethod
    def resolve_active_nodes(state: ClusterState, updated_nodes_ids: set[UUID4]) -> tuple[ClusterState, set[UUID4]]:
        for node_id in list(updated_nodes_ids):
            node: Node = state.ids_to_nodes_mapping[node_id]

            if node.status != NodeStatus.ACTIVE:
                continue

            node._was_updated = False
            updated_nodes_ids.remove(node_id)

        return state, updated_nodes_ids


class ServiceUpdatesResolver:
    @staticmethod
    def run(state: ClusterState) -> ClusterState:
        updated_services_ids: set[UUID4] = set(pluck_attr("id", filter(lambda obj: obj._was_updated, state.services)))

        state, updated_services_ids = ServiceUpdatesResolver.delete_instances_of_deleted_services(
            state, updated_services_ids
        )
        state, updated_services_ids = ServiceUpdatesResolver.check_instances_of_active_services(
            state, updated_services_ids
        )

        if len(updated_services_ids) != 0:
            raise SchedulingError("Not all updated services resolved")

        return state

    @staticmethod
    def delete_instances_of_deleted_services(
        state: ClusterState, updated_services_ids: set[UUID4]
    ) -> tuple[ClusterState, set[UUID4]]:
        for service_id in list(updated_services_ids):
            service: Service = state.ids_to_services_mapping[service_id]

            if service.status != ServiceStatus.DELETED:
                continue

            instance: ServiceInstance = state.ids_to_service_instances_mapping[service.instance_id]
            if instance.node_id:
                state.evict_instance(instance)

            service._was_updated = False
            updated_services_ids.remove(service_id)

        return state, updated_services_ids

    @staticmethod
    def check_instances_of_active_services(
        state: ClusterState, updated_services_ids: set[UUID4]
    ) -> tuple[ClusterState, set[UUID4]]:
        for service_id in list(updated_services_ids):
            service: Service = state.ids_to_services_mapping[service_id]

            if service.status != ServiceStatus.ACTIVE:
                continue
            if service.instance_id:
                instance: ServiceInstance = state.ids_to_service_instances_mapping[service.instance_id]
            else:
                instance = ServiceInstance(
                    executable=service.executable,
                    status=ServiceInstanceStatus.EVICTED,
                    service_id=service.id,
                )
                ServiceInstanceModel.synchronize_schema(instance)
                # Link to service
                service.instance_id = instance.id
                # Add to cluster state
                state.service_instances.append(instance)
                state.ids_to_service_instances_mapping[instance.id] = instance
            instance._was_updated = True

            service._was_updated = False
            updated_services_ids.remove(service_id)

        return state, updated_services_ids


class ServiceInstanceUpdatesResolver:
    @staticmethod
    def run(state: ClusterState) -> ClusterState:
        updated_service_instances_ids: set[UUID4] = set(
            pluck_attr("id", filter(lambda obj: obj._was_updated, state.service_instances))
        )

        state.calculate_available_resources()

        state, updated_service_instances_ids = ServiceInstanceUpdatesResolver.resolve_placed_service_instances(
            state, updated_service_instances_ids
        )
        state, updated_service_instances_ids = ServiceInstanceUpdatesResolver.resolve_evicted_service_instances(
            state, updated_service_instances_ids
        )

        state.metrics.increase_counter(TrackedObjects.EVICTED, len(updated_service_instances_ids))

        return state

    @staticmethod
    def resolve_placed_service_instances(
        state: ClusterState, updated_service_instances_ids: set[UUID4]
    ) -> tuple[ClusterState, set[UUID4]]:
        for instance_id in list(updated_service_instances_ids):
            instance: ServiceInstance = state.ids_to_service_instances_mapping[instance_id]

            if instance.status != ServiceInstanceStatus.PLACED:
                continue

            if instance.resource_status != ResourceStatus.OK:
                state = ServiceInstanceUpdatesResolver.resolve_constraint_service_instance(state, instance)

            service: Service = state.ids_to_services_mapping[instance.service_id]
            state.shrink_instance(instance, service.resource_limit)
            updated_service_instances_ids.remove(instance_id)

        return state, updated_service_instances_ids

    @staticmethod
    def resolve_constraint_service_instance(
            state: ClusterState, instance: ServiceInstance
    ) -> ClusterState:
        constraint_resource_type = instance.resource_status.value

        service: Service = state.ids_to_services_mapping[instance.service_id]
        current_node = state.ids_to_nodes_mapping[instance.node_id]

        increased_resources = ServiceInstanceUpdatesResolver._calculate_increased_resources(
            service, instance, constraint_resource_type
        )

        # Attempt to increase resources without moving
        additional_resources = increased_resources - instance.allocated_resources
        evict = state.attempt_to_acquire_resources(current_node, additional_resources, service, same_or_lower_type_with_lower_priority)
        if evict is not None:
            for evicted_instance in evict:
                state.evict_instance(evicted_instance, current_node)
            instance.allocated_resources += additional_resources
            current_node.available_resources -= additional_resources

            instance.resource_status = ResourceStatus.OK
            return state

        # Attempt to increase resources by moving
        for node in (obj for obj in state.active_nodes() if obj.id != current_node.id):
            evict = state.attempt_to_acquire_resources(
                node, increased_resources, service, same_or_lower_type_with_lower_priority
            )
            if evict is not None:
                for evicted_instance in evict:
                    state.evict_instance(evicted_instance, node)
                state.evict_instance(instance, current_node)
                state.place_instance(instance, node, increased_resources)

            instance.resource_status = ResourceStatus.OK
            return state

        return state

    @staticmethod
    def resolve_evicted_service_instances(
        state: ClusterState, updated_service_instances_ids: set[UUID4]
    ) -> tuple[ClusterState, set[UUID4]]:

        for instance_id in list(updated_service_instances_ids):
            instance: ServiceInstance = state.ids_to_service_instances_mapping[instance_id]

            if instance.status != ServiceInstanceStatus.EVICTED:
                continue

            service: Service = state.ids_to_services_mapping[instance.service_id]
            required_resources = base_allocated_resources.get_compliant(service.resource_limit, service.resource_floor)

            is_placed = ServiceInstanceUpdatesResolver.place_instance_somewhere(
                state, instance, required_resources, service
            )
            if is_placed:
                updated_service_instances_ids.remove(instance_id)
            else:
                pass  # Resolve not enough resources to place

        return state, updated_service_instances_ids

    @staticmethod
    def _calculate_increased_resources(
        service: Service, instance: ServiceInstance, exceeded_resource_type: str
    ) -> ResourceData:
        resource_limit = getattr(service.resource_limit, exceeded_resource_type)
        resource_allocated = getattr(instance.allocated_resources, exceeded_resource_type)

        if resource_limit == resource_allocated:
            return instance.allocated_resources
        resource_increased = min(
            resource_limit, resource_allocated + increase_resource_step_kwargs[exceeded_resource_type]
        ) if resource_limit else resource_allocated + increase_resource_step_kwargs[exceeded_resource_type]

        return ResourceData(**(instance.allocated_resources.dict() | {exceeded_resource_type: resource_increased}))

    @staticmethod
    def place_instance_somewhere(
        state: ClusterState, instance: ServiceInstance, required_resources: ResourceData, service: Service
    ) -> bool:
        for node in state.active_nodes():  # Try to place instance without evictions
            try:
                state.place_instance(instance, node, required_resources)
                return True
            except SchedulingError:
                continue
        chosen_node = None
        for node in state.active_nodes():  # Try to place instance with evictions
            evict = state.attempt_to_acquire_resources(
                node, required_resources, service, same_or_lower_type_with_lower_priority
            )
            if evict is not None:
                chosen_node = node
                if all(map(lambda x: x.type != ServiceType, state.get_node_services(node))):
                    break

        if chosen_node:
            for evicted_instance in evict:
                state.evict_instance(evicted_instance, node)
            state.place_instance(instance, node, required_resources)
            return True
        return False
