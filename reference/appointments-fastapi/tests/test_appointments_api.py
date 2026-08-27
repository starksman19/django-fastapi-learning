from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, time, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


def create_catalog(client):
    day = datetime.now(UTC).date() + timedelta(days=7)
    specialist = client.post(
        "/api/v1/specialists",
        json={
            "name": "Anna Nowak",
            "email": f"anna-{uuid4()}@example.com",
            "timezone": "UTC",
        },
    ).json()
    service = client.post(
        "/api/v1/services",
        json={
            "specialist_id": specialist["id"],
            "name": "Konsultacja",
            "duration_minutes": 30,
            "price": "150.00",
        },
    ).json()
    rule_response = client.post(
        "/api/v1/availability-rules",
        json={
            "specialist_id": specialist["id"],
            "weekday": day.weekday(),
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "starts_on": day.isoformat(),
        },
    )
    assert rule_response.status_code == 201
    return specialist, service, day


def booking_payload(specialist, service, day):
    starts_at = datetime.combine(day, time(10, 0), tzinfo=UTC)
    return {
        "specialist_id": specialist["id"],
        "service_id": service["id"],
        "customer_name": "Jan Kowalski",
        "customer_email": "jan@example.com",
        "starts_at": starts_at.isoformat(),
    }


def test_requires_api_key():
    with TestClient(app) as anonymous:
        response = anonymous.get("/api/v1/specialists")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_failed"


def test_catalog_pagination_and_available_slots(client):
    specialist, service, day = create_catalog(client)
    response = client.get("/api/v1/specialists?limit=1&search=Anna")
    assert response.status_code == 200
    assert response.json()["total"] == 1

    slots = client.get(f"/api/v1/available-slots?service_id={service['id']}&day={day.isoformat()}")
    assert slots.status_code == 200
    assert len(slots.json()) > 0
    assert slots.json()[0]["starts_at"].endswith("Z")


def test_booking_is_idempotent_and_can_be_cancelled(client):
    specialist, service, day = create_catalog(client)
    payload = booking_payload(specialist, service, day)
    headers = {"Idempotency-Key": "appointment-1"}

    first = client.post("/api/v1/appointments", json=payload, headers=headers)
    replay = client.post("/api/v1/appointments", json=payload, headers=headers)
    assert first.status_code == replay.status_code == 201
    assert first.json()["id"] == replay.json()["id"]
    assert replay.headers["Idempotency-Replayed"] == "true"

    confirmed = client.post(f"/api/v1/appointments/{first.json()['id']}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    cancelled = client.post(f"/api/v1/appointments/{first.json()['id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_idempotency_key_rejects_changed_request(client):
    specialist, service, day = create_catalog(client)
    payload = booking_payload(specialist, service, day)
    client.post("/api/v1/appointments", json=payload, headers={"Idempotency-Key": "same-key"})
    payload["customer_name"] = "Inna osoba"
    response = client.post(
        "/api/v1/appointments", json=payload, headers={"Idempotency-Key": "same-key"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "idempotency_key_reused"


def test_cancellation_releases_slot_for_another_booking(client):
    specialist, service, day = create_catalog(client)
    payload = booking_payload(specialist, service, day)
    first = client.post(
        "/api/v1/appointments",
        json=payload,
        headers={"Idempotency-Key": "cancel-first"},
    )
    assert first.status_code == 201
    assert client.post(f"/api/v1/appointments/{first.json()['id']}/cancel").status_code == 200

    second = client.post(
        "/api/v1/appointments",
        json=payload,
        headers={"Idempotency-Key": "book-after-cancel"},
    )
    assert second.status_code == 201
    assert second.json()["id"] != first.json()["id"]


def test_unavailable_exception_removes_all_slots(client):
    specialist, service, day = create_catalog(client)
    response = client.post(
        "/api/v1/availability-exceptions",
        json={
            "specialist_id": specialist["id"],
            "exception_date": day.isoformat(),
            "available": False,
            "reason": "Urlop",
        },
    )
    assert response.status_code == 201
    slots = client.get(f"/api/v1/available-slots?service_id={service['id']}&day={day.isoformat()}")
    assert slots.status_code == 200
    assert slots.json() == []


@pytest.mark.concurrency
def test_only_one_parallel_booking_succeeds(client, api_key):
    specialist, service, day = create_catalog(client)
    payload = booking_payload(specialist, service, day)

    def book(key):
        with TestClient(app, headers={"X-API-Key": api_key}) as parallel_client:
            return parallel_client.post(
                "/api/v1/appointments",
                json=payload,
                headers={"Idempotency-Key": key},
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(book, ["parallel-1", "parallel-2"]))

    assert sorted(statuses) == [201, 409]
