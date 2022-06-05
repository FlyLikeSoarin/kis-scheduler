from funcy import first

from app.models import NodeModel, ServiceInstanceModel, ServiceModel
from app.scheduler import Scheduler
from app.schemas.helpers import ResourceData, base_allocated_resources, increase_resource_step_kwargs
from app.schemas.nodes import NodeStatus
from app.schemas.services import ResourceStatus, ServiceInstanceStatus, ServiceType

from .factories import NodeFactory, ServiceFactory, ServiceInstanceFactory


class TestServiceCreation:
    def test_service_is_placed_on_node_with_enough_resources(self):
        """
        If there is an active service without instance and node with required resources to run instance,
        when service instance will be placed on aforementioned node on next scheduling.
        """
        node = NodeFactory.create(was_updated=False)
        service = ServiceFactory.create(was_updated=True)

        Scheduler.run_scheduling()

        instance = first(ServiceInstanceModel.retrieve_schemas())
        assert instance
        assert str(instance.service_id) == str(service.id)  # Instance linked to service
        assert str(instance.node_id) == str(node.id)  # Instance placed on the only node

    def test_when_node_fails_instances_from_this_node_will_be_rescheduled(self, test_client):
        """
        If there is an active service with running instance, node on which instance is placed
        and another node with required resources to run instance,
        when if occupied node fails instance will be place on other node on next scheduling.
        """
        nodes = (
            NodeFactory.create(was_updated=True, status=NodeStatus.FAILED.value),
            NodeFactory.create(was_updated=False, status=NodeStatus.ACTIVE.value),
        )
        service = ServiceFactory.create(was_updated=False)
        ServiceInstanceFactory.create(was_updated=False, service=service, host_node=nodes[0])

        Scheduler.run_scheduling()

        instance = first(ServiceInstanceModel.retrieve_schemas())
        assert instance
        assert str(instance.service_id) == str(service.id)  # Instance linked to service
        assert str(instance.node_id) == str(nodes[1].id)  # Instance placed on the only node

    def test_node_with_higher_priority_preempts_node_with_lower_priority_on_scarce_resources(self, test_client):
        """
        If there is an active service with running instance, node on which instance is placed
        with resources for one node and another service without instance and higher priority,
        when running instance will be preempted and new instance will be allocated if there are no available resources.
        """
        node = NodeFactory.create(  # Enough resources for single instance
            was_updated=False, **(base_allocated_resources.dict())
        )
        ordinary = ServiceFactory.create(was_updated=False, priority=0)
        ServiceInstanceFactory.create(was_updated=False, service=ordinary, host_node=node)
        important = ServiceFactory.create(was_updated=True, priority=99)

        Scheduler.run_scheduling()

        ordinary_instances = ServiceInstanceModel.retrieve_schemas_where(
            ServiceInstanceModel.service_id == ordinary.id
        )
        important_instances = ServiceInstanceModel.retrieve_schemas_where(ServiceInstanceModel.service == important.id)
        assert ordinary_instances and important_instances

        assert first(ordinary_instances).node_id is None  # Preempted low-priority instance
        assert str(first(important_instances).node_id) == str(node.id)  # Placed high-priority instance

    def test_node_with_lower_priority_not_preempts_node_with_higher_priority_on_scarce_resources(self, test_client):
        """
        If there is an active service with running instance, node on which instance is placed
        with resources for one node and another service without instance and lower priority,
        when running instance will not be preempted.
        """
        node = NodeFactory.create(  # Enough resources for single instance
            was_updated=False, **(base_allocated_resources.dict())
        )
        ordinary = ServiceFactory.create(was_updated=True, priority=0)
        important = ServiceFactory.create(was_updated=False, priority=99)
        ServiceInstanceFactory.create(
            was_updated=False,
            executable=important.executable,
            service=important,
            host_node=node,
        )

        Scheduler.run_scheduling()

        ordinary_instances = ServiceInstanceModel.retrieve_schemas_where(
            ServiceInstanceModel.service_id == ordinary.id
        )
        important_instances = ServiceInstanceModel.retrieve_schemas_where(ServiceInstanceModel.service == important.id)
        assert ordinary_instances and important_instances

        assert first(ordinary_instances).node_id is None  # Not placed low-priority instance
        assert str(first(important_instances).node_id) == str(node.id)  # Unchanged high-priority instance

    def test_node_with_highest_priority_will_be_places(self, test_client):
        """
        If there is an active service without running instances
        and node on which instance is placed with resources for one node,
        when instance for service with the highest priority will be placed.
        """
        node = NodeFactory.create(  # Enough resources for single instance
            was_updated=False, **(base_allocated_resources.dict())
        )
        ServiceFactory.create(was_updated=True, priority=0)
        ServiceFactory.create(was_updated=True, priority=50)
        important = ServiceFactory.create(was_updated=True, priority=99)

        Scheduler.run_scheduling()

        important_instances = ServiceInstanceModel.retrieve_schemas_where(ServiceInstanceModel.service_id == important.id)
        assert important_instances
        assert str(first(important_instances).node_id) == str(node.id)  # Placed highest-priority instance

    def test_node_placed_without_eviction_if_resources_available_on_same_node(self, test_client):
        """
        If there is an active service with running instance, node on which instance is placed
        with enough resources for both and another service without instance and higher priority,
        when running instance will not be preempted and new instance will be places on same node.
        """
        node = NodeFactory.create(was_updated=False)  # Enough resources for both by default
        # Stateless
        ordinary = ServiceFactory.create(was_updated=False, priority=0)
        ServiceInstanceFactory.create(was_updated=False, service=ordinary, host_node=node)
        # Fragile
        important = ServiceFactory.create(was_updated=True, priority=99)

        Scheduler.run_scheduling()

        ordinary_instances = ServiceInstanceModel.retrieve_schemas_where(
            ServiceInstanceModel.service_id == ordinary.id
        )
        importnant_instances = ServiceInstanceModel.retrieve_schemas_where(ServiceInstanceModel.service == important.id)
        assert ordinary_instances and importnant_instances

        assert str(first(ordinary_instances).node_id) == str(node.id)  # Unchanged low-priority instance
        assert str(first(importnant_instances).node_id) == str(node.id)  # Placed high-priority instance

    def test_node_placed_without_eviction_if_resources_available_on_other_node(self, test_client):
        """
        If there is an active service with running instance, node on which instance is placed,
        unoccupied node (both with resources for one node) and another service without instance and higher priority,
        when running instance will not be preempted and new instance will be placed on unoccupied node.
        """
        nodes = NodeFactory.create_batch(  # Enough resources for single instance on each node
            size=2, was_updated=False, **(base_allocated_resources.dict())
        )
        # Stateless
        ordinary = ServiceFactory.create(was_updated=False, priority=0)
        ServiceInstanceFactory.create(was_updated=False, service=ordinary, host_node=nodes[0])
        # Fragile
        important = ServiceFactory.create(was_updated=True, priority=99)

        Scheduler.run_scheduling()

        ordinary_instances = ServiceInstanceModel.retrieve_schemas_where(
            ServiceInstanceModel.service_id == ordinary.id
        )
        important_instances = ServiceInstanceModel.retrieve_schemas_where(ServiceInstanceModel.service == important.id)
        assert ordinary_instances and important_instances

        assert str(first(ordinary_instances).node_id) == str(nodes[0].id)  # Unchanged low-priority instance
        assert str(first(important_instances).node_id) == str(nodes[1].id)  # Placed high-priority instance

    def test_if_node_exceeds_resource_more_will_be_allocated_if_allowed_by_limit_and_possible(self, test_client):
        """
        If there is an active service
        with high enough limit and running instance which exceeded cpu_cores allocation,
        and host node with enough available resources,
        when allocation will be increased.
        """
        expected_resources = base_allocated_resources + ResourceData(
            cpu_cores=increase_resource_step_kwargs["cpu_cores"]
        )

        node = NodeFactory.create(was_updated=False)
        service = ServiceFactory.create(was_updated=False, cpu_cores_limit=100.0)
        ServiceInstanceFactory.create(
            was_updated=True,
            status=ServiceInstanceStatus.PLACED,
            resource_status=ResourceStatus.CONSTRAINT_BY_CPU,
            service=service,
            host_node=node,
            **(base_allocated_resources.dict()),
        )

        Scheduler.run_scheduling()

        instance = first(ServiceInstanceModel.retrieve_schemas())
        assert instance
        assert str(instance.node_id) == str(node.id)
        assert instance.allocated_resources == expected_resources

    def test_if_node_exceeds_resource_more_will_not_be_allocated_if_not_allowed_by_limit(self, test_client):
        """
        If there are an active service with running instance which exceeded cpu_cores allocation and reached limit,
        and host node with enough available resources, when allocation will not be increased.
        """
        expected_resources = base_allocated_resources

        node = NodeFactory.create(was_updated=False)
        service = ServiceFactory.create(was_updated=False, cpu_cores=expected_resources.cpu_cores)
        ServiceInstanceFactory.create(
            was_updated=True,
            status=ServiceInstanceStatus.PLACED,
            resource_status=ResourceStatus.CONSTRAINT_BY_CPU,
            service=service,
            host_node=node,
            **(base_allocated_resources.dict()),
        )

        Scheduler.run_scheduling()

        instance = first(ServiceInstanceModel.retrieve_schemas())
        assert instance
        assert str(instance.node_id) == str(node.id)
        assert instance.allocated_resources == expected_resources

    def test_if_node_exceeds_resource_more_will_not_be_allocated_if_allowed_by_limit_but_not_possible(
        self, test_client
    ):
        """
        If there are an active service
        with high enough limit and running instance which exceeded cpu_cores allocation,
        and node with not enough available resources,
        when allocation will be increased.
        """
        expected_resources = base_allocated_resources

        node = NodeFactory.create(was_updated=False, cpu_cores=expected_resources.cpu_cores)
        service = ServiceFactory.create(was_updated=False, cpu_cores=100.0)
        ServiceInstanceFactory.create(
            was_updated=True,
            status=ServiceInstanceStatus.PLACED,
            resource_status=ResourceStatus.CONSTRAINT_BY_CPU,
            service=service,
            host_node=node,
            **(base_allocated_resources.dict()),
        )

        Scheduler.run_scheduling()

        instance = first(ServiceInstanceModel.retrieve_schemas())
        assert instance
        assert str(instance.node_id) == str(node.id)
        assert instance.allocated_resources == expected_resources

    def test_if_node_exceeds_resource_more_will_be_allocated_if_allowed_by_limit_and_possible_by_preemption(
        self, test_client
    ):
        """
        If there are an active service
        with high enough limit and running instance which exceeded cpu_cores allocation,
        and host node with enough available resources (after preemption),
        when allocation will be increased.
        """
        expected_resources = base_allocated_resources + ResourceData(
            cpu_cores=increase_resource_step_kwargs["cpu_cores"]
        )

        node = NodeFactory.create(was_updated=False, cpu_cores=base_allocated_resources.cpu_cores * 2)
        ordinary = ServiceFactory.create(was_updated=False, priority=0)
        important = ServiceFactory.create(was_updated=False, priority=99, cpu_cores_limit=100.0)
        ServiceInstanceFactory.create(
            was_updated=False,
            service=ordinary,
            host_node=node,
            **(base_allocated_resources.dict()),
        )
        ServiceInstanceFactory.create(
            was_updated=True,
            status=ServiceInstanceStatus.PLACED,
            resource_status=ResourceStatus.CONSTRAINT_BY_CPU,
            service=important,
            host_node=node,
            **(base_allocated_resources.dict()),
        )

        Scheduler.run_scheduling()

        preempted_instance = first(
            ServiceInstanceModel.retrieve_schemas_where(ServiceInstanceModel.service_id == ordinary.id)
        )
        important_instance = first(
            ServiceInstanceModel.retrieve_schemas_where(ServiceInstanceModel.service_id == important.id)
        )
        assert preempted_instance and important_instance

        assert preempted_instance.node_id is None
        assert str(important_instance.node_id) == str(node.id)
        assert important_instance.allocated_resources == expected_resources
