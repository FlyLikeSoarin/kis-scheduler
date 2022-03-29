import pytest

from uuid import uuid4

from app.models import NodeModel

from .factories import NodeFactory


class TestServiceCreation:
    def test_a(self, test_client):
        response = test_client.get('/api/services/')

        NodeFactory.create_batch(size=2, is_operational=True)
        NodeModel.create(id=uuid4(), status='unknown')
        node = NodeModel(id=uuid4(), status='deleted')
        node.save()

        assert list(NodeModel.select().where(NodeModel.status == 'unknown').execute()) == []

