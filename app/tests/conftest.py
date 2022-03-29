import pytest

from fastapi.testclient import TestClient
from peewee import Database, SqliteDatabase

from app.main import app
from app.models import NodeModel, ServiceModel, ServiceInstanceModel

MODELS = [NodeModel, ServiceModel, ServiceInstanceModel]


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def test_db(mocker) -> Database:
    test_db = SqliteDatabase('./test.db')
    test_db.bind(MODELS)
    test_db.connect()
    test_db.create_tables(MODELS)

    mocked_db = mocker.patch('app.database.db', autospec=True)
    mocked_db.return_value = test_db

    yield test_db

    test_db.drop_tables(MODELS)
    test_db.close()
