from app.models import ServiceInstanceModel

from .factories import NodeFactory, ServiceFactory, ServiceInstanceFactory


class TestForeignKeys:
    def test_foreign_keys_set_in_schemas(self):
        node = NodeFactory.create()
        service_1, service_2 = ServiceFactory.create_batch(size=2)

        ServiceInstanceFactory.create(service=service_1.id, host_node=node.id)
        ServiceInstanceFactory.create(service=service_2.id, host_node=node.id)

        service_instances_s = ServiceInstanceModel.retrieve_schemas()

        assert service_instances_s
        assert str(service_instances_s[0].service_id) == service_1.id and str(service_instances_s[0].node_id) == node.id
        assert str(service_instances_s[1].service_id) == service_2.id and str(service_instances_s[1].node_id) == node.id
