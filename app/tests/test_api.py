import json
from datetime import timedelta
from functools import partial
from uuid import uuid4

from funcy import lmap, omit

from app.models import NodeModel, SchedulerLogModel, ServiceModel
from app.schemas.monitoring import SchedulerLog, SchedulerMetrics
from app.schemas.nodes import NodeStatus
from app.schemas.services import ExecutionStatus, ResourceStatus, ServiceInstanceStatus, ServiceStatus, ServiceType

from .factories import NodeFactory, ServiceFactory, ServiceInstanceFactory


class TestNodeCRUDAndListAPI:
    def test_create_node(self, test_client):
        response = test_client.post(
            "/api/nodes/",
            json={"node_resources": {"cpu_cores": 4.0, "ram": "16GiB", "disk": "1TiB"}},
        )
        assert NodeModel.get(id=response.json()["data"]["id"]) is not None
        assert omit(response.json()["data"], "id") == {
            "status": NodeStatus.ACTIVE.value,
            "node_resources": {"cpu_cores": 4.0, "ram": 16 * (1024**3), "disk": 1024**4},
            "available_resources": None,
            "instance_ids": None,
        }

    def test_create_node_422_if_not_valid(self, test_client):
        response = test_client.post(
            "/api/nodes/",
            json={"node_resources": "KIS"},
        )
        assert response.status_code == 422

    def test_delete_node_404_if_not_found(self, test_client):
        response = test_client.delete(f"/api/nodes/{uuid4()}/")
        assert response.status_code == 404

    def test_delete_node(self, test_client):
        node = NodeFactory.create()
        response = test_client.delete(f"/api/nodes/{node.id}/")
        assert response.json()["data"] == _serialize_node_model(
            node, status=NodeStatus.DELETED.value, node_resources=None
        )

    def test_retrieve_node_404_if_not_found(self, test_client):
        response = test_client.get(f"/api/nodes/{uuid4()}/")
        assert response.status_code == 404

    def test_retrieve_node(self, test_client):
        node = NodeFactory.create()
        response = test_client.get(f"/api/nodes/{node.id}/")
        assert response.json()["data"] == _serialize_node_model(node)

    def test_list_node_returns_empty_list_if_no_services_exists(self, test_client):
        response = test_client.get("/api/nodes/")
        assert response.json()["data"] == []

    def test_list_node_returns_list_with_every_service(self, test_client):
        nodes = NodeFactory.create_batch(size=3)
        response = test_client.get("/api/nodes/")
        assert response.json()["data"] == lmap(_serialize_node_model, nodes)


class TestServiceCRUDAndListAPI:
    def test_create_service(self, test_client):
        executable = str(uuid4())
        response = test_client.post(
            "/api/services/",
            json={
                "executable": executable,
                "type": ServiceType.FRAGILE.value,
                "resource_limit": {"cpu_cores": 1.5, "ram": "1GiB", "disk": "10GiB"},
                "resource_floor": {"cpu_cores": 1.5, "ram": "1GiB", "disk": "10GiB"},
            },
        )
        assert ServiceModel.get(id=response.json()["data"]["id"]) is not None
        assert omit(response.json()["data"], "id") == {
            "executable": executable,
            "status": ServiceStatus.ACTIVE.value,
            "type": ServiceType.FRAGILE.value,
            "priority": 99,
            "resource_limit": {"cpu_cores": 1.5, "ram": 1024**3, "disk": (1024**3) * 10},
            "resource_floor": {"cpu_cores": 1.5, "ram": 1024**3, "disk": (1024**3) * 10},
            "instance_id": None,
        }

    def test_create_service_422_if_not_valid(self, test_client):
        response = test_client.post(
            "/api/services/",
            json={"type": "KIS"},
        )
        assert response.status_code == 422

    def test_update_service_with_priority(self, test_client):
        new_executable = str(uuid4())
        service = ServiceFactory.create()
        response = test_client.patch(
            f"/api/services/{service.id}/",
            json={"executable": new_executable},
        )
        assert response.json()["data"] == _serialize_service_model(service, executable=new_executable)

    def test_update_service_with_priority(self, test_client):
        service = ServiceFactory.create()
        response = test_client.patch(
            f"/api/services/{service.id}/",
            json={"priority": 1},
        )
        assert response.json()["data"] == _serialize_service_model(service, priority=1)

    def test_update_service_with_resource_limit(self, test_client):
        service = ServiceFactory.create()
        response = test_client.patch(
            f"/api/services/{service.id}/",
            json={"resource_limit": {"cpu_cores": 1.5, "ram": "1GiB", "disk": "10GiB"}},
        )
        assert response.json()["data"] == _serialize_service_model(
            service, resource_limit={"cpu_cores": 1.5, "ram": 1024**3, "disk": (1024**3) * 10}
        )

    def test_update_service_with_resource_floor(self, test_client):
        service = ServiceFactory.create()
        response = test_client.patch(
            f"/api/services/{service.id}/",
            json={"resource_floor": {"cpu_cores": 1.5, "ram": "1GiB", "disk": "10GiB"}},
        )
        assert response.json()["data"] == _serialize_service_model(
            service, resource_floor={"cpu_cores": 1.5, "ram": 1024**3, "disk": (1024**3) * 10}
        )

    def test_update_service_422_if_not_valid(self, test_client):
        service = ServiceFactory.create()
        response = test_client.patch(
            f"/api/services/{service.id}/",
            json={"resource_limit": "KIS"},
        )
        assert response.status_code == 422

    def test_delete_service_404_if_not_found(self, test_client):
        response = test_client.delete(f"/api/services/{uuid4()}/")
        assert response.status_code == 404

    def test_delete_service(self, test_client):
        service = ServiceFactory.create()
        response = test_client.delete(f"/api/services/{service.id}/")
        assert response.json()["data"] == _serialize_service_model(
            service, status=ServiceStatus.DELETED.value, resource_limit=None, resource_floor=None
        )

    def test_retrieve_service_404_if_not_found(self, test_client):
        response = test_client.get(f"/api/services/{uuid4()}/")
        assert response.status_code == 404

    def test_retrieve_service(self, test_client):
        service = ServiceFactory.create()
        response = test_client.get(f"/api/services/{service.id}/")
        assert response.json()["data"] == _serialize_service_model(service)

    def test_list_services_returns_empty_list_if_no_services_exists(self, test_client):
        response = test_client.get("/api/services/")
        assert response.json()["data"] == []

    def test_list_services_returns_list_with_every_service(self, test_client):
        services = ServiceFactory.create_batch(size=3)
        response = test_client.get("/api/services/")
        assert response.json()["data"] == lmap(_serialize_service_model, services)


class TestMonitoringAPI:
    def test_retrieve_cluster_state(self, test_client):
        nodes = NodeFactory.create_batch(size=3)
        services = ServiceFactory.create_batch(size=3)
        service_instances = ServiceInstanceFactory.create_batch(size=3)

        response = test_client.get("/api/monitoring/state/")

        assert response.json() == {
            "status": "OK",
            "nodes": lmap(partial(_serialize_node_model, instance_ids=[]), nodes),
            "services": lmap(_serialize_service_model, services),
            "service_instances": lmap(_serialize_service_instance_model, service_instances),
        }

    def test_retrieve_metrics(self, test_client):
        logs = self._create_logs()
        response = test_client.get("/api/monitoring/metrics/")
        assert response.json()["data"] == [json.loads(log.json()) for log in logs]

    def test_retrieve_metrics_starting_from_timestamp(self, test_client):
        logs = self._create_logs()
        response = test_client.get(f"/api/monitoring/metrics/?from={logs[2].timestamp}")
        assert response.json()["data"] == [json.loads(log.json()) for log in logs[3:]]

    def test_retrieve_metrics_by_period_duration(self, test_client):
        logs = self._create_logs()
        response = test_client.get(f"/api/monitoring/metrics/?duration={timedelta(minutes=1)}")
        assert response.json()["data"] == [json.loads(log.json()) for log in logs]

    @staticmethod
    def _create_logs():
        logs = []
        for _ in range(5):
            log = SchedulerLog(metrics=SchedulerMetrics())
            SchedulerLogModel.persist_schema(log)
            logs.append(log)
        return logs


class TestEventsAPI:
    def test_node_event_ok(self, test_client):
        node = NodeFactory.create()
        response = test_client.post(
            "/api/events/nodes/", json={"node_id": node.id, "updated_status": NodeStatus.ACTIVE.value}
        )
        assert response.status_code == 200

    def test_node_event_validation(self, test_client):
        node = NodeFactory.create()
        response = test_client.post(
            "/api/events/nodes/", json={"node_id": node.id, "updated_status": NodeStatus.DELETED}
        )
        assert response.status_code == 422

    def test_service_instance_event_ok_with_execution_status (self, test_client):
        service_instance = ServiceInstanceFactory.create()
        response = test_client.post(
            "/api/events/service-instances/",
            json={"instance_id": service_instance.id, "execution_status": ExecutionStatus.RUNNING},
        )
        assert response.status_code == 200

    def test_service_instance_event_ok_with_resource_status (self, test_client):
        service_instance = ServiceInstanceFactory.create()
        response = test_client.post(
            "/api/events/service-instances/",
            json={"instance_id": service_instance.id, "resource_status": ResourceStatus.CONSTRAINT_BY_CPU},
        )
        assert response.status_code == 200

    def test_service_instance_event_validation(self, test_client):
        service_instance = ServiceInstanceFactory.create()
        response = test_client.post(
            "/api/events/service-instances/",
            json={"instance_id": service_instance.id, "resource_status": ExecutionStatus.RUNNING},
        )
        assert response.status_code == 422


def _serialize_node_model(node_model, **kwargs):
    return {
        "id": str(node_model.id),
        "status": node_model.status,
        "node_resources": {
            "cpu_cores": node_model.cpu_cores,
            "disk": node_model.disk,
            "ram": node_model.ram,
        },
        "available_resources": None,
        "instance_ids": None,
    } | kwargs


def _serialize_service_model(service_model, **kwargs):
    return {
        "id": str(service_model.id),
        "executable": str(service_model.executable),
        "status": service_model.status,
        "type": service_model.type,
        "priority": service_model.priority,

        "resource_limit": {
            "cpu_cores": service_model.cpu_cores_limit,
            "disk": service_model.disk_limit,
            "ram": service_model.ram_limit,
        },
        "resource_floor": {
            "cpu_cores": service_model.cpu_cores_floor,
            "disk": service_model.disk_floor,
            "ram": service_model.ram_floor,
        },

        "instance_id": None,
    } | kwargs


def _serialize_service_instance_model(service_instance_model, **kwargs):
    return {
        "id": str(service_instance_model.id),
        "executable": str(service_instance_model.executable),
        "status": service_instance_model.status,
        "execution_status": service_instance_model.execution_status,
        "resource_status": service_instance_model.resource_status,

        "allocated_resources": {
            "cpu_cores": service_instance_model.cpu_cores,
            "disk": service_instance_model.disk,
            "ram": service_instance_model.ram,
        },

        "node_id": None,
        "service_id": None,
    } | kwargs
