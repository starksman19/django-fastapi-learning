from decimal import Decimal

from rest_framework import serializers

from inventory.models import Order, OrderItem, Product, Reservation, Stock, Warehouse


class ProductSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))

    class Meta:
        model = Product
        fields = ["id", "sku", "name", "description", "price", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ["id", "code", "name", "created_at"]
        read_only_fields = ["id", "created_at"]


class StockSerializer(serializers.ModelSerializer):
    available = serializers.IntegerField(read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)

    class Meta:
        model = Stock
        fields = [
            "id",
            "product",
            "product_sku",
            "warehouse",
            "warehouse_code",
            "quantity",
            "reserved",
            "available",
            "updated_at",
        ]
        read_only_fields = ["id", "reserved", "available", "updated_at"]

    def validate_quantity(self, value):
        reserved = self.instance.reserved if self.instance else 0
        if value < reserved:
            raise serializers.ValidationError("Stan nie może być mniejszy niż aktywne rezerwacje.")
        return value


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ["id", "stock", "quantity", "status", "created_at", "updated_at"]


class OrderItemSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    reservation = ReservationSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_sku",
            "warehouse",
            "warehouse_code",
            "quantity",
            "unit_price",
            "reservation",
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "customer_email",
            "status",
            "total_amount",
            "items",
            "created_at",
            "updated_at",
        ]


class OrderItemInputSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(active=True))
    warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    customer_email = serializers.EmailField()
    items = OrderItemInputSerializer(many=True, allow_empty=False)

    def validate_items(self, items):
        pairs = [(item["product"].id, item["warehouse"].id) for item in items]
        if len(pairs) != len(set(pairs)):
            raise serializers.ValidationError(
                "Produkt i magazyn mogą wystąpić w zamówieniu tylko raz."
            )
        return items
