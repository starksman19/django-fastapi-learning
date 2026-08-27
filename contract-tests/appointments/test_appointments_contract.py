from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, time, timedelta
from uuid import uuid4

import requests


def url(client, path):
    return f"{client.base_url}{path}"


def create_schedule(client):
    suffix = uuid4().hex[:10]
    day = datetime.now(UTC).date() + timedelta(days=7)
    specialist_response = client.post(
        url(client, "/api/v1/specialists"),
        json={
            "name": "Specjalista",
            "email": f"specialist-{suffix}@example.com",
            "timezone": "UTC",
        },
        timeout=10,
    )
    assert specialist_response.status_code == 201
    specialist = specialist_response.json()
    service_response = client.post(
        url(client, "/api/v1/services"),
        json={
            "specialist_id": specialist["id"],
            "name": "Konsultacja",
            "duration_minutes": 30,
            "price": "100.00",
        },
        timeout=10,
    )
    assert service_response.status_code == 201
    service = service_response.json()
    rule_response = client.post(
        url(client, "/api/v1/availability-rules"),
        json={
            "specialist_id": specialist["id"],
            "weekday": day.weekday(),
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "starts_on": day.isoformat(),
        },
        timeout=10,
    )
    assert rule_response.status_code == 201
    return specialist, service, day


def booking_payload(specialist, service, day):
    return {
        "specialist_id": specialist["id"],
        "service_id": service["id"],
        "customer_name": "Klient kontraktowy",
        "customer_email": "client@example.com",
        "starts_at": datetime.combine(day, time(10), tzinfo=UTC).isoformat(),
    }


def test_health_and_authentication_contract(appointments_client):
    health = appointments_client.get(url(appointments_client, "/health"), timeout=5)
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    without_key = appointments_client.get(
        url(appointments_client, "/api/v1/specialists"), headers={"X-API-Key": ""}, timeout=5
    )
    assert without_key.status_code == 401
    assert set(without_key.json()["error"]) == {"code", "message", "details"}


def test_slots_idempotency_and_state_machine(appointments_client):
    specialist, service, day = create_schedule(appointments_client)
    slots = appointments_client.get(
        url(appointments_client, "/api/v1/available-slots"),
        params={"service_id": service["id"], "day": day.isoformat()},
        timeout=10,
    )
    assert slots.status_code == 200
    assert slots.json()

    payload = booking_payload(specialist, service, day)
    headers = {"Idempotency-Key": f"contract-{uuid4()}"}
    first = appointments_client.post(
        url(appointments_client, "/api/v1/appointments"), json=payload, headers=headers, timeout=10
    )
    replay = appointments_client.post(
        url(appointments_client, "/api/v1/appointments"), json=payload, headers=headers, timeout=10
    )
    assert first.status_code == replay.status_code == 201
    assert first.json()["id"] == replay.json()["id"]

    confirmed = appointments_client.post(
        url(appointments_client, f"/api/v1/appointments/{first.json()['id']}/confirm"), timeout=10
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"


def test_same_slot_cannot_be_booked_twice(appointments_client):
    specialist, service, day = create_schedule(appointments_client)
    payload = booking_payload(specialist, service, day)

    def book():
        return requests.post(
            url(appointments_client, "/api/v1/appointments"),
            json=payload,
            headers={
                "X-API-Key": appointments_client.headers["X-API-Key"],
                "Idempotency-Key": f"parallel-{uuid4()}",
            },
            timeout=15,
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: book(), range(2)))
    assert sorted(statuses) == [201, 409]
