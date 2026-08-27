from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import requests


def url(client, path):
    return f"{client.base_url}{path}"


def create_stocked_product(client, quantity=1):
    suffix = uuid4().hex[:10]
    product_response = client.post(
        url(client, "/api/v1/products/"),
        json={"sku": f"SKU-{suffix}", "name": "Produkt kontraktowy", "price": "25.00"},
        timeout=10,
    )
    assert product_response.status_code == 201
    warehouse_response = client.post(
        url(client, "/api/v1/warehouses/"),
        json={"code": f"W-{suffix}", "name": "Magazyn kontraktowy"},
        timeout=10,
    )
    assert warehouse_response.status_code == 201
    stock_response = client.post(
        url(client, "/api/v1/stocks/"),
        json={
            "product": product_response.json()["id"],
            "warehouse": warehouse_response.json()["id"],
            "quantity": quantity,
        },
        timeout=10,
    )
    assert stock_response.status_code == 201
    return product_response.json(), warehouse_response.json(), stock_response.json()


def order_payload(product, warehouse, quantity=1):
    return {
        "customer_email": "contract@example.com",
        "items": [{"product": product["id"], "warehouse": warehouse["id"], "quantity": quantity}],
    }


def test_health_and_authentication_contract(inventory_client):
    health = inventory_client.get(url(inventory_client, "/health/"), timeout=5)
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    without_key = inventory_client.get(
        url(inventory_client, "/api/v1/products/"), headers={"X-API-Key": ""}, timeout=5
    )
    assert without_key.status_code == 401
    assert set(without_key.json()["error"]) == {"code", "message", "details"}


def test_order_idempotency_and_release_contract(inventory_client):
    product, warehouse, stock = create_stocked_product(inventory_client, quantity=1)
    payload = order_payload(product, warehouse)
    key = f"contract-{uuid4()}"
    headers = {"Idempotency-Key": key}

    first = inventory_client.post(
        url(inventory_client, "/api/v1/orders/"), json=payload, headers=headers, timeout=10
    )
    replay = inventory_client.post(
        url(inventory_client, "/api/v1/orders/"), json=payload, headers=headers, timeout=10
    )
    assert first.status_code == replay.status_code == 201
    assert first.json()["id"] == replay.json()["id"]
    assert replay.headers["Idempotency-Replayed"] == "true"

    cancelled = inventory_client.post(
        url(inventory_client, f"/api/v1/orders/{first.json()['id']}/cancel/"), timeout=10
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    refreshed_stock = inventory_client.get(
        url(inventory_client, f"/api/v1/stocks/{stock['id']}/"), timeout=10
    )
    assert refreshed_stock.json()["available"] == 1


def test_last_item_is_not_oversold(inventory_client):
    product, warehouse, _ = create_stocked_product(inventory_client, quantity=1)
    payload = order_payload(product, warehouse)

    def buy():
        return requests.post(
            url(inventory_client, "/api/v1/orders/"),
            json=payload,
            headers={
                "X-API-Key": inventory_client.headers["X-API-Key"],
                "Idempotency-Key": f"parallel-{uuid4()}",
            },
            timeout=15,
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: buy(), range(2)))
    assert sorted(statuses) == [201, 409]
