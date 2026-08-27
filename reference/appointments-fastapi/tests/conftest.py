import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import get_settings
from app.database import engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE appointments, availability_exceptions, availability_rules, "
                "services, specialists "
                "RESTART IDENTITY CASCADE"
            )
        )
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        test_client.headers["X-API-Key"] = get_settings().appointments_api_key
        yield test_client


@pytest.fixture
def api_key():
    return os.getenv("APPOINTMENTS_API_KEY", get_settings().appointments_api_key)
