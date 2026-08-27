import uuid

from django.db import models
from django.db.models import F, Q


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "sku"]
        indexes = [models.Index(fields=["active", "name"], name="product_active_name_idx")]
        constraints = [
            models.CheckConstraint(condition=Q(price__gt=0), name="product_price_positive")
        ]


class Warehouse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]


class Stock(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stocks")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="stocks")
    quantity = models.PositiveIntegerField(default=0)
    reserved = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["warehouse_id", "product_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "warehouse"], name="stock_product_warehouse_uniq"
            ),
            models.CheckConstraint(condition=Q(quantity__gte=0), name="stock_quantity_nonnegative"),
            models.CheckConstraint(condition=Q(reserved__gte=0), name="stock_reserved_nonnegative"),
            models.CheckConstraint(
                condition=Q(reserved__lte=F("quantity")), name="stock_reserved_lte_quantity"
            ),
        ]
        indexes = [
            models.Index(fields=["warehouse", "product"], name="stock_warehouse_product_idx")
        ]

    @property
    def available(self) -> int:
        return self.quantity - self.reserved


class Order(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Potwierdzone"
        COMPLETED = "completed", "Zrealizowane"
        CANCELLED = "cancelled", "Anulowane"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_email = models.EmailField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.CONFIRMED)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="order_status_created_idx"),
            models.Index(fields=["customer_email"], name="order_customer_email_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(total_amount__gte=0), name="order_total_nonnegative")
        ]


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product", "warehouse"],
                name="order_item_order_product_warehouse_uniq",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0), name="order_item_quantity_positive"
            ),
            models.CheckConstraint(condition=Q(unit_price__gt=0), name="order_item_price_positive"),
        ]


class Reservation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Aktywna"
        RELEASED = "released", "Zwolniona"
        CONSUMED = "consumed", "Zużyta"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_item = models.OneToOneField(
        OrderItem, on_delete=models.CASCADE, related_name="reservation"
    )
    stock = models.ForeignKey(Stock, on_delete=models.PROTECT, related_name="reservations")
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0), name="reservation_quantity_positive"
            )
        ]
        indexes = [
            models.Index(
                fields=["stock", "status"],
                condition=Q(status="active"),
                name="reservation_active_stock_idx",
            )
        ]


class IdempotencyRecord(models.Model):
    key = models.CharField(max_length=255, unique=True)
    request_hash = models.CharField(max_length=64)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="idempotency_record")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["created_at"], name="idempotency_created_idx")]
