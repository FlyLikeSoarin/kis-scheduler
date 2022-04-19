import random
from typing import Callable

import pytest
from funcy import first, lmap
from matplotlib import pyplot as plt

from app.models import SchedulerLogModel
from app.scheduler import Scheduler
from app.schemas.helpers import ResourceDatag
from app.schemas.monitoring import TrackedAction, TrackedObjects
from app.schemas.requests import CreateNodeRequest, CreateServiceRequest, UpdateServiceRequest
from app.schemas.responses import NodeResponse, ServiceResponse
from app.schemas.services import ServiceType


class TestingConfig:
    service_type_probs: tuple[float, float, float] = (0.6, 0.3, 0.1)

    stateless_size_probs: tuple[float, float, float, float] = (0.6, 0.3, 0.1, 0.0)
    fragile_size_probs: tuple[float, float, float, float] = (0.0, 0.3, 0.4, 0.3)
    stateful_size_probs: tuple[float, float, float, float] = (0.25, 0.25, 0.25, 0.25)

    nodes_per_size: tuple[int, int, float, float] = (0, 0, 5, 0)

    service_actions_at_epoch: Callable[[int], dict] = lambda self, epoch: {"created": 1, "updated": 0, "deleted": 0}

    def get_service_size_probs(self, service_type):
        return {
            ServiceType.STATELESS: self.stateless_size_probs,
            ServiceType.FRAGILE: self.fragile_size_probs,
            ServiceType.STATEFUL: self.stateful_size_probs,
        }.get(service_type)


class TestPerformance:
    sizes = ("small", "medium", "big", "mega")
    types = (ServiceType.STATELESS, ServiceType.FRAGILE, ServiceType.STATEFUL)

    service_size_presets = {
        "small": ResourceData(cpu_cores=1.0, ram="2GiB", disk="10GiB"),
        "medium": ResourceData(cpu_cores=2.0, ram="4GiB", disk="40GiB"),
        "big": ResourceData(cpu_cores=4.0, ram="8GiB", disk="100GiB"),
        "mega": ResourceData(cpu_cores=16.0, ram="64Gib", disk="1TiB"),
    }

    node_size_presets = {
        "small": ResourceData(cpu_cores=8.0, ram="64GiB", disk="1TiB"),
        "medium": ResourceData(cpu_cores=12.0, ram="128GiB", disk="8TiB"),
        "big": ResourceData(cpu_cores=16.0, ram="128GiB", disk="8TiB"),
        "mega": ResourceData(cpu_cores=28.0, ram="256Gib", disk="40TiB"),
    }

    @pytest.fixture(autouse=True)
    def setup(self, test_client):
        self.client = test_client

        self.services = []
        self.nodes = []

    def test_performance(self):
        self.run_performance_test()

    def run_performance_test(self, epochs=5, testing_config=TestingConfig()):
        for size, amount in zip(self.sizes, testing_config.nodes_per_size):
            for _ in range(amount):
                self.nodes.append(self._create_node(size=size))

        for epoch in range(epochs):
            service_actions = testing_config.service_actions_at_epoch(epoch)
            for _ in range(service_actions["created"]):
                self.services.append(self._create_service(*self._get_service_params(testing_config)))
            for _ in range(service_actions["updated"]):
                service_id = random.choice(self.services)
                self._update_service(
                    service_id,
                    self._get_service_params(testing_config)[0],
                )
            for _ in range(service_actions["deleted"]):
                service_id = random.choice(self.services)
                index = self.services.index(self._create_service(service_id))
                self.services.pop(index)

            Scheduler.run_scheduling()

        logs = SchedulerLogModel.retrieve_schemas()
        x = list(range(1, epochs + 1))
        times = lmap(lambda log: log.metrics.duration.microseconds, logs)

        allocs = lmap(lambda log: log.metrics.actions_counter.get(TrackedAction.ALLOCATION, 0), logs)
        evicts = lmap(lambda log: log.metrics.actions_counter.get(TrackedAction.EVICTION, 0), logs)

        services = lmap(lambda log: log.metrics.objects_counter.get(TrackedObjects.SERVICE, 0), logs)
        evicted = lmap(lambda log: log.metrics.objects_counter.get(TrackedObjects.EVICTED, 0), logs)

        cpu_utilization = lmap(lambda log: log.metrics.utilization["cpu_cores"], logs)
        ram_utilization = lmap(lambda log: log.metrics.utilization["ram"], logs)
        disk_utilization = lmap(lambda log: log.metrics.utilization["disk"], logs)

        fig = plt.figure()
        # plt.plot(x, times, label='Scheduler run duration')

        # plt.plot(x, allocs, label='Number of allocations')
        # plt.plot(x, evicts, label='Number of evictions')

        # plt.plot(x, services, label='Number of allocations')
        # plt.plot(x, evicted, label='Number of evictions')

        plt.plot(x, cpu_utilization, label="Cpu utilisation")
        plt.plot(x, ram_utilization, label="Ram utilisation")
        plt.plot(x, disk_utilization, label="Disk utilisation")

        plt.legend()
        plt.savefig("temp.png", dpi=fig.dpi)

    def _get_service_params(self, testing_config):
        service_type = first(random.choices(self.types, testing_config.service_type_probs))
        size = first(random.choices(self.sizes, testing_config.get_service_size_probs(service_type)))
        return size, service_type

    # --- Service actions ----
    def _create_service(self, size="medium", type_=ServiceType.STATELESS):
        request_body = CreateServiceRequest(
            type=type_,
            resource_limit=self.service_size_presets.get(size),
        )

        response = self.client.post("/api/services/", json=request_body.dict())
        service_response = ServiceResponse.parse_raw(response.text)
        return service_response.data.id

    def _update_service(self, service_id, size="medium"):
        request_body = UpdateServiceRequest(
            resource_limit=self.service_size_presets.get(size),
        )

        response = self.client.patch(f"/api/services/{str(service_id)}", json=request_body.dict())
        service_response = ServiceResponse.parse_raw(response.text)
        return service_response.data.id

    def _delete_service(self, service_id):
        response = self.client.delete(f"/api/services/{str(service_id)}")
        service_response = ServiceResponse.parse_raw(response.text)
        return service_response.data.id

    # --- Node actions ----
    def _create_node(self, size="medium"):
        request_body = CreateNodeRequest(
            node_resources=self.node_size_presets.get(size),
        )

        response = self.client.post("/api/nodes/", json=request_body.dict())
        node_response = NodeResponse.parse_raw(response.text)
        return node_response.data.id

    def _delete_node(self, service_id):
        response = self.client.delete(f"/api/nodes/{str(service_id)}")
        node_response = NodeResponse.parse_raw(response.text)
        return node_response.data.id
