from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from inventory.views import OrderViewSet, ProductViewSet, StockViewSet, WarehouseViewSet, health


router = DefaultRouter()
router.register("products", ProductViewSet)
router.register("warehouses", WarehouseViewSet)
router.register("stocks", StockViewSet)
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("health/", health, name="health"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/", include(router.urls)),
]
