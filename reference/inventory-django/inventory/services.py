import hashlib
import json
from decimal import Decimal

from django.db import connection, transaction

from inventory.exceptions import DomainConflict
from inventory.models import IdempotencyRecord, Order, OrderItem, Reservation, Stock


def _payload_hash(customer_email: str, items: list[dict]) -> str:
    normalized_items = sorted(
        [
            {
                "product_id": str(item["product"].id),
                "warehouse_id": str(item["warehouse"].id),
                "quantity": item["quantity"],
            }
            for item in items
        ],
        key=lambda item: (item["product_id"], item["warehouse_id"]),
    )
    raw = json.dumps(
        {"customer_email": customer_email.lower(), "items": normalized_items},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _advisory_lock(key: str) -> None:
    lock_id = int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "big", signed=True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_id])


@transaction.atomic
def create_order(
    *, customer_email: str, items: list[dict], idempotency_key: str
) -> tuple[Order, bool]:
    request_hash = _payload_hash(customer_email, items)
    _advisory_lock(idempotency_key)

    existing = IdempotencyRecord.objects.select_related("order").filter(key=idempotency_key).first()
    if existing:
        if existing.request_hash != request_hash:
            raise DomainConflict(
                "Ten klucz idempotencji został użyty z innym żądaniem.",
                code="idempotency_key_reused",
            )
        return existing.order, True

    product_ids = {item["product"].id for item in items}
    warehouse_ids = {item["warehouse"].id for item in items}
    locked_stocks = (
        Stock.objects.select_for_update()
        .filter(
            product_id__in=product_ids,
            warehouse_id__in=warehouse_ids,
        )
        .order_by("pk")
    )
    stock_by_pair = {(stock.product_id, stock.warehouse_id): stock for stock in locked_stocks}

    for item in items:
        pair = (item["product"].id, item["warehouse"].id)
        stock = stock_by_pair.get(pair)
        if stock is None:
            raise DomainConflict(
                "Brak stanu produktu w wybranym magazynie.", code="stock_not_found"
            )
        if stock.available < item["quantity"]:
            raise DomainConflict("Niewystarczający dostępny zapas.", code="insufficient_stock")

    order = Order.objects.create(customer_email=customer_email, status=Order.Status.CONFIRMED)
    total = Decimal("0.00")
    for item in items:
        stock = stock_by_pair[(item["product"].id, item["warehouse"].id)]
        stock.reserved += item["quantity"]
        stock.save(update_fields=["reserved", "updated_at"])
        order_item = OrderItem.objects.create(
            order=order,
            product=item["product"],
            warehouse=item["warehouse"],
            quantity=item["quantity"],
            unit_price=item["product"].price,
        )
        Reservation.objects.create(
            order_item=order_item,
            stock=stock,
            quantity=item["quantity"],
        )
        total += item["product"].price * item["quantity"]

    order.total_amount = total
    order.save(update_fields=["total_amount", "updated_at"])
    IdempotencyRecord.objects.create(key=idempotency_key, request_hash=request_hash, order=order)
    return order, False


@transaction.atomic
def cancel_order(order_id) -> Order:
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status == Order.Status.CANCELLED:
        return order
    if order.status != Order.Status.CONFIRMED:
        raise DomainConflict(
            "Tylko potwierdzone zamówienie można anulować.", code="invalid_order_transition"
        )

    reservations = list(
        Reservation.objects.select_for_update()
        .filter(order_item__order=order, status=Reservation.Status.ACTIVE)
        .order_by("stock_id")
    )
    stocks = {
        stock.id: stock
        for stock in Stock.objects.select_for_update()
        .filter(id__in={reservation.stock_id for reservation in reservations})
        .order_by("pk")
    }
    for reservation in reservations:
        stock = stocks[reservation.stock_id]
        stock.reserved -= reservation.quantity
        stock.save(update_fields=["reserved", "updated_at"])
        reservation.status = Reservation.Status.RELEASED
        reservation.save(update_fields=["status", "updated_at"])

    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def complete_order(order_id) -> Order:
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status == Order.Status.COMPLETED:
        return order
    if order.status != Order.Status.CONFIRMED:
        raise DomainConflict(
            "Tylko potwierdzone zamówienie można zrealizować.", code="invalid_order_transition"
        )

    reservations = list(
        Reservation.objects.select_for_update()
        .filter(order_item__order=order, status=Reservation.Status.ACTIVE)
        .order_by("stock_id")
    )
    stocks = {
        stock.id: stock
        for stock in Stock.objects.select_for_update()
        .filter(id__in={reservation.stock_id for reservation in reservations})
        .order_by("pk")
    }
    for reservation in reservations:
        stock = stocks[reservation.stock_id]
        stock.quantity -= reservation.quantity
        stock.reserved -= reservation.quantity
        stock.save(update_fields=["quantity", "reserved", "updated_at"])
        reservation.status = Reservation.Status.CONSUMED
        reservation.save(update_fields=["status", "updated_at"])

    order.status = Order.Status.COMPLETED
    order.save(update_fields=["status", "updated_at"])
    return order
