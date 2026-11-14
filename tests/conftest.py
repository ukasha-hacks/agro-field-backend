import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="session")
def client():
    with TestClient(create_app()) as instance:
        yield instance
