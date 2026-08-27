import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Order",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("customer_email", models.EmailField(max_length=254)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("confirmed", "Potwierdzone"),
                            ("completed", "Zrealizowane"),
                            ("cancelled", "Anulowane"),
                        ],
                        default="confirmed",
                        max_length=16,
                    ),
                ),
                ("total_amount", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["status", "-created_at"], name="order_status_created_idx"),
                    models.Index(fields=["customer_email"], name="order_customer_email_idx"),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("total_amount__gte", 0)), name="order_total_nonnegative"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("sku", models.CharField(max_length=64, unique=True)),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["name", "sku"],
                "indexes": [
                    models.Index(fields=["active", "name"], name="product_active_name_idx")
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("price__gt", 0)), name="product_price_positive"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="Warehouse",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("code", models.CharField(max_length=32, unique=True)),
                ("name", models.CharField(max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["code"]},
        ),
        migrations.CreateModel(
            name="IdempotencyRecord",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("key", models.CharField(max_length=255, unique=True)),
                ("request_hash", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="idempotency_record",
                        to="inventory.order",
                    ),
                ),
            ],
            options={
                "indexes": [models.Index(fields=["created_at"], name="idempotency_created_idx")]
            },
        ),
        migrations.CreateModel(
            name="Stock",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("quantity", models.PositiveIntegerField(default=0)),
                ("reserved", models.PositiveIntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stocks",
                        to="inventory.product",
                    ),
                ),
                (
                    "warehouse",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stocks",
                        to="inventory.warehouse",
                    ),
                ),
            ],
            options={
                "ordering": ["warehouse_id", "product_id"],
                "indexes": [
                    models.Index(
                        fields=["warehouse", "product"], name="stock_warehouse_product_idx"
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("product", "warehouse"), name="stock_product_warehouse_uniq"
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("quantity__gte", 0)), name="stock_quantity_nonnegative"
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("reserved__gte", 0)), name="stock_reserved_nonnegative"
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("reserved__lte", models.F("quantity"))),
                        name="stock_reserved_lte_quantity",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("quantity", models.PositiveIntegerField()),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=12)),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="inventory.order",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="order_items",
                        to="inventory.product",
                    ),
                ),
                (
                    "warehouse",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="order_items",
                        to="inventory.warehouse",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("order", "product", "warehouse"),
                        name="order_item_order_product_warehouse_uniq",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("quantity__gt", 0)), name="order_item_quantity_positive"
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("unit_price__gt", 0)), name="order_item_price_positive"
                    ),
                ]
            },
        ),
        migrations.CreateModel(
            name="Reservation",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("quantity", models.PositiveIntegerField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Aktywna"),
                            ("released", "Zwolniona"),
                            ("consumed", "Zużyta"),
                        ],
                        default="active",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "order_item",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reservation",
                        to="inventory.orderitem",
                    ),
                ),
                (
                    "stock",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reservations",
                        to="inventory.stock",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        condition=models.Q(("status", "active")),
                        fields=["stock", "status"],
                        name="reservation_active_stock_idx",
                    )
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("quantity__gt", 0)),
                        name="reservation_quantity_positive",
                    )
                ],
            },
        ),
    ]
