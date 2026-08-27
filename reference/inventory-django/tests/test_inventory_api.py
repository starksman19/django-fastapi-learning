from concurrent.futures import ThreadPoolExecutor

import pytest
from django.conf import settings
from django.db import close_old_connections, connections
from rest_framework.test import APIClient

from inventory.models import Order, Product, Stock, Warehouse


pytestmark = pytest.mark.django_db


def api_client() -> APIClient:
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=settings.INVENTORY_API_KEY)
    return client


@pytest.fixture
def catalog():
    product = Product.objects.create(sku="SKU-1", name="Klawiatura", price="100.00")
    warehouse = Warehouse.objects.create(code="WAW", name="Warszawa")
    stock = Stock.objects.create(product=product, warehouse=warehouse, quantity=2)
    return product, warehouse, stock


def order_payload(product, warehouse, quantity=1):
    return {
        "customer_email": "buyer@example.com",
        "items": [
            {"product": str(product.id), "warehouse": str(warehouse.id), "quantity": quantity}
        ],
    }


def test_requires_api_key():
    response = APIClient().get("/api/v1/products/")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_failed"


def test_product_crud_and_pagination():
    client = api_client()
    response = client.post(
        "/api/v1/products/",
        {"sku": "SKU-CRUD", "name": "Monitor", "price": "999.99", "active": True},
        format="json",
    )
    assert response.status_code == 201
    product_id = response.json()["id"]

    response = client.get("/api/v1/products/?search=Monitor&page_size=1")
    assert response.status_code == 200
    assert response.json()["count"] == 1

    response = client.patch(f"/api/v1/products/{product_id}/", {"price": "899.99"}, format="json")
    assert response.status_code == 200
    assert response.json()["price"] == "899.99"


def test_order_is_idempotent_and_cancel_releases_stock(catalog):
    product, warehouse, stock = catalog
    client = api_client()
    payload = order_payload(product, warehouse)

    first = client.post("/api/v1/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY="order-1")
    replay = client.post("/api/v1/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY="order-1")

    assert first.status_code == replay.status_code == 201
    assert first.json()["id"] == replay.json()["id"]
    assert replay.headers["Idempotency-Replayed"] == "true"
    stock.refresh_from_db()
    assert stock.reserved == 1

    cancelled = client.post(f"/api/v1/orders/{first.json()['id']}/cancel/")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    stock.refresh_from_db()
    assert stock.reserved == 0


def test_idempotency_key_rejects_different_payload(catalog):
    product, warehouse, _ = catalog
    client = api_client()
    client.post(
        "/api/v1/orders/",
        order_payload(product, warehouse, quantity=1),
        format="json",
        HTTP_IDEMPOTENCY_KEY="same-key",
    )
    response = client.post(
        "/api/v1/orders/",
        order_payload(product, warehouse, quantity=2),
        format="json",
        HTTP_IDEMPOTENCY_KEY="same-key",
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "idempotency_key_reused"


def test_order_rolls_back_when_one_item_has_insufficient_stock(catalog):
    product, warehouse, stock = catalog
    unavailable_product = Product.objects.create(
        sku="NO-STOCK", name="Niedostępny produkt", price="50.00"
    )
    Stock.objects.create(product=unavailable_product, warehouse=warehouse, quantity=0)
    payload = {
        "customer_email": "rollback@example.com",
        "items": [
            {"product": str(product.id), "warehouse": str(warehouse.id), "quantity": 1},
            {
                "product": str(unavailable_product.id),
                "warehouse": str(warehouse.id),
                "quantity": 1,
            },
        ],
    }

    response = api_client().post(
        "/api/v1/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY="rollback-order"
    )
    assert response.status_code == 409
    assert Order.objects.count() == 0
    stock.refresh_from_db()
    assert stock.reserved == 0


@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
def test_only_one_client_can_buy_last_item():
    product = Product.objects.create(sku="LAST-ONE", name="Ostatnia sztuka", price="10.00")
    warehouse = Warehouse.objects.create(code="LAST", name="Magazyn")
    stock = Stock.objects.create(product=product, warehouse=warehouse, quantity=1)
    payload = order_payload(product, warehouse)

    def place_order(key):
        close_old_connections()
        try:
            response = api_client().post(
                "/api/v1/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY=key
            )
            return response.status_code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(place_order, ["parallel-1", "parallel-2"]))

    assert sorted(statuses) == [201, 409]
    stock.refresh_from_db()
    assert stock.reserved == 1
