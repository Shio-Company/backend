from django.urls import include, path
from rest_framework.routers import SimpleRouter

from base.views.authentication import (
    GoogleLoginView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
    TokenRefreshView,
)
from base.views.catalog import (
    AdminCategoryViewSet,
    AdminDropViewSet,
    AdminProductImageViewSet,
    AdminProductVariationViewSet,
    AdminProductViewSet,
    CategoryViewSet,
    DropViewSet,
    InventorySummaryView,
    ProductViewSet,
)
from base.views.health import health_check
from base.views.inventory import StockAdjustView

app_name = "base"

router = SimpleRouter()
router.register("drops", DropViewSet, basename="drop")
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")

admin_router = SimpleRouter()
admin_router.register("drops", AdminDropViewSet, basename="admin-drop")
admin_router.register("categories", AdminCategoryViewSet, basename="admin-category")
admin_router.register("products", AdminProductViewSet, basename="admin-product")
admin_router.register("product-images", AdminProductImageViewSet, basename="admin-product-image")
admin_router.register("product-variations", AdminProductVariationViewSet, basename="admin-product-variation")

urlpatterns = [
    # ── auth (prefixo api/auth/) ──────────────────────────────────────────────
    # POST - Cadastro com e-mail e senha
    path("auth/register/", RegisterView.as_view(), name="register"),
    # POST - Login com e-mail e senha
    path("auth/login/", LoginView.as_view(), name="login"),
    # POST - Recebe id_token do Google e retorna JWT + dados do user
    path("auth/google/", GoogleLoginView.as_view(), name="google-login"),
    # POST - Renova o access token com o refresh token
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    # POST - Invalida o refresh token (logout)
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    # GET - Retorna dados do utilizador autenticado
    path("auth/me/", MeView.as_view(), name="me"),
    # ── health (prefixo api/) ─────────────────────────────────────────────────
    path("health/", health_check, name="health_check"),
    # ── catalog público (sem prefixo) ────────────────────────────────────────
    path("", include(router.urls)),
    # ── admin (staff) ─────────────────────────────────────────────────────────
    path("admin/", include(admin_router.urls)),
    path("admin/inventory/", InventorySummaryView.as_view(), name="inventory_summary"),
    path(
        "admin/stock/<int:variation_id>/adjust/",
        StockAdjustView.as_view(),
        name="admin-stock-adjust",
    ),
]
