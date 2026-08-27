from django.db import connection, transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import mixins, status, viewsets
from rest_framework import serializers
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from inventory.models import Order, Product, Stock, Warehouse
from inventory.serializers import (
    OrderCreateSerializer,
    OrderSerializer,
    ProductSerializer,
    StockSerializer,
    WarehouseSerializer,
)
from inventory.services import cancel_order, complete_order, create_order


@extend_schema(
    auth=[],
    responses={
        200: inline_serializer(
            name="InventoryHealth",
            fields={
                "status": serializers.CharField(),
                "service": serializers.CharField(),
            },
        )
    },
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return Response({"status": "ok", "service": "inventory-django"})


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filterset_fields = ["active"]
    search_fields = ["sku", "name", "description"]
    ordering_fields = ["sku", "name", "price", "created_at"]


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    search_fields = ["code", "name"]
    ordering_fields = ["code", "name", "created_at"]


class StockViewSet(viewsets.ModelViewSet):
    queryset = Stock.objects.select_related("product", "warehouse")
    serializer_class = StockSerializer
    filterset_fields = ["product", "warehouse"]
    search_fields = ["product__sku", "product__name", "warehouse__code"]
    ordering_fields = ["quantity", "reserved", "updated_at"]

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = get_object_or_404(
            self.get_queryset().select_for_update(),
            pk=kwargs["pk"],
        )
        self.check_object_permissions(request, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Order.objects.prefetch_related(
        "items__product", "items__warehouse", "items__reservation"
    )
    filterset_fields = ["status", "customer_email"]
    search_fields = ["customer_email", "id"]
    ordering_fields = ["created_at", "updated_at", "total_amount"]

    def get_serializer_class(self):
        return OrderCreateSerializer if self.action == "create" else OrderSerializer

    @extend_schema(request=OrderCreateSerializer, responses={201: OrderSerializer})
    def create(self, request, *args, **kwargs):
        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            raise ValidationError({"Idempotency-Key": ["Ten nagłówek jest wymagany."]})
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order, replayed = create_order(
            customer_email=serializer.validated_data["customer_email"],
            items=serializer.validated_data["items"],
            idempotency_key=idempotency_key,
        )
        output = OrderSerializer(order, context=self.get_serializer_context())
        headers = {"Idempotency-Replayed": str(replayed).lower()}
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

    @extend_schema(request=None, responses={200: OrderSerializer})
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        get_object_or_404(Order, pk=pk)
        order = cancel_order(pk)
        return Response(OrderSerializer(order, context=self.get_serializer_context()).data)

    @extend_schema(request=None, responses={200: OrderSerializer})
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        get_object_or_404(Order, pk=pk)
        order = complete_order(pk)
        return Response(OrderSerializer(order, context=self.get_serializer_context()).data)
