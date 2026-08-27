import os

import pytest
import requests


@pytest.fixture(scope="session")
def inventory_client():
    session = requests.Session()
    session.headers["X-API-Key"] = os.getenv("INVENTORY_API_KEY", "dev-inventory-api-key")
    session.base_url = os.getenv("INVENTORY_BASE_URL", "http://localhost:8001")
    return session


@pytest.fixture(scope="session")
def appointments_client():
    session = requests.Session()
    session.headers["X-API-Key"] = os.getenv("APPOINTMENTS_API_KEY", "dev-appointments-api-key")
    session.base_url = os.getenv("APPOINTMENTS_BASE_URL", "http://localhost:8002")
    return session
