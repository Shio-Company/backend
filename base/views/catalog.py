import logging

import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import filters, mixins, status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from base.models.catalog import Category, Drop, Product, ProductImage, ProductVariation
from base.serializers.catalog import (
    AdminCategorySerializer,
    AdminDropSerializer,
    AdminProductImageSerializer,
    AdminProductSerializer,
    AdminProductVariationSerializer,
    CategorySerializer,
    DropDetailSerializer,
    DropListSerializer,
    InventorySummarySerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)
from base.services.catalog import InventoryService

logger = logging.getLogger(__name__)


class InventorySummaryView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Admin - Inventory"],
        summary="Resumo de inventário",
        description=(
            "Retorna um resumo agregado do inventário de produtos ativos.\n\n"
            "**Campos:**\n"
            "- `total_products` — total de produtos com `is_active=true`\n"
            "- `total_stock` — soma de `available_quantity` de todos os produtos ativos\n"
            "- `low_stock_count` — produtos ativos com `available_quantity ≤ minimum_quantity` (padrão: 5)\n\n"
            "**Requer:** `is_staff=true`."
        ),
        responses={
            200: OpenApiResponse(
                response=InventorySummarySerializer,
                description="Resumo calculado com sucesso.",
                examples=[
                    OpenApiExample(
                        name="Resumo",
                        value={"total_products": 42, "total_stock": 1280, "low_stock_count": 5},
                        response_only=True,
                        status_codes=["200"],
                    )
                ],
            ),
            401: OpenApiResponse(description="Não autenticado."),
            403: OpenApiResponse(description="Acesso negado — requer is_staff."),
        },
    )
    def get(self, request):
        data = InventoryService.get_summary()
        serializer = InventorySummarySerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProductFilter(django_filters.FilterSet):
    drop = django_filters.CharFilter(field_name="drop__slug")
    category = django_filters.CharFilter(field_name="category__slug")

    class Meta:
        model = Product
        fields = ["drop", "category"]


@extend_schema_view(
    list=extend_schema(
        tags=["Catalog"],
        summary="Lista drops ativos",
        description="Lista pública e paginada dos drops com lançamento liberado.",
        responses=DropListSerializer,
    ),
    retrieve=extend_schema(
        tags=["Catalog"],
        summary="Detalhe do drop",
        description="Drop por slug, com os produtos ativos pertencentes a ele.",
        responses=DropDetailSerializer,
    ),
)
class DropViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    lookup_field = "slug"
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]

    def get_queryset(self):
        return Drop.objects.active_now()

    def get_serializer_class(self):
        return DropDetailSerializer if self.action == "retrieve" else DropListSerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Catalog"],
        summary="Lista categorias",
        description="Lista pública e paginada das categorias ativas.",
        responses=CategorySerializer,
    ),
    retrieve=extend_schema(
        tags=["Catalog"],
        summary="Detalhe da categoria",
        responses=CategorySerializer,
    ),
)
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    lookup_field = "slug"
    serializer_class = CategorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        return Category.objects.filter(is_active=True)


@extend_schema_view(
    list=extend_schema(
        tags=["Catalog"],
        summary="Lista produtos disponíveis",
        description=(
            "Lista pública e paginada de produtos disponíveis. "
            "Filtros: `?drop={slug}`, `?category={slug}`; busca: `?search=`."
        ),
        responses=ProductListSerializer,
    ),
    retrieve=extend_schema(
        tags=["Catalog"],
        summary="Detalhe do produto",
        description="Produto por slug, com imagens e disponibilidade de estoque.",
        responses=ProductDetailSerializer,
    ),
)
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "description"]

    def get_queryset(self):
        return (
            Product.objects.available()
            .select_related("category", "drop")
            .prefetch_related("images", "variations__stock")
        )

    def get_serializer_class(self):
        return ProductDetailSerializer if self.action == "retrieve" else ProductListSerializer


# ─── Admin CRUD (staff) ──────────────────────────────────────────────────────

_TAG = ["Admin - Catalog"]


@extend_schema_view(
    list=extend_schema(
        tags=_TAG,
        summary="Listar drops",
        description=(
            "Lista **todos** os drops (incluindo inativos e com `launch_date` futura), paginado.\n\n"
            "Difere do catálogo público que exibe apenas drops ativos e já lançados."
        ),
    ),
    create=extend_schema(
        tags=_TAG,
        summary="Criar drop",
        description=(
            "Cria um novo drop.\n\n"
            "Dica: defina `is_active=false` para manter em rascunho e ative quando estiver pronto "
            "para publicação no catálogo."
        ),
    ),
    retrieve=extend_schema(
        tags=_TAG,
        summary="Detalhe do drop",
        description="Retorna todos os campos do drop pelo ID, incluindo timestamps.",
    ),
    update=extend_schema(
        tags=_TAG,
        summary="Atualizar drop (PUT)",
        description="Substituição completa — todos os campos obrigatórios devem ser enviados.",
    ),
    partial_update=extend_schema(exclude=True),
    destroy=extend_schema(
        tags=_TAG,
        summary="Remover drop",
        description=(
            "Remove permanentemente o drop. Os produtos associados não são removidos "
            "(o campo `drop` é anulado)."
        ),
    ),
)
class AdminDropViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    http_method_names = ["get", "post", "put", "delete", "head", "options"]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    queryset = Drop.objects.all()
    serializer_class = AdminDropSerializer


@extend_schema_view(
    list=extend_schema(
        tags=_TAG,
        summary="Listar categorias",
        description="Lista **todas** as categorias (incluindo inativas), paginado.",
    ),
    create=extend_schema(
        tags=_TAG,
        summary="Criar categoria",
        description="Cria uma nova categoria.",
    ),
    retrieve=extend_schema(
        tags=_TAG,
        summary="Detalhe da categoria",
        description="Retorna todos os campos da categoria pelo ID.",
    ),
    update=extend_schema(
        tags=_TAG,
        summary="Atualizar categoria (PUT)",
        description="Substituição completa — todos os campos obrigatórios devem ser enviados.",
    ),
    partial_update=extend_schema(exclude=True),
    destroy=extend_schema(
        tags=_TAG,
        summary="Remover categoria",
        description=(
            "Remove permanentemente a categoria. Produtos associados ficam sem categoria "
            "(campo `category` anulado)."
        ),
    ),
)
class AdminCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    http_method_names = ["get", "post", "put", "delete", "head", "options"]
    queryset = Category.objects.all()
    serializer_class = AdminCategorySerializer


@extend_schema_view(
    list=extend_schema(
        tags=_TAG,
        summary="Listar produtos",
        description=(
            "Lista **todos** os produtos (incluindo inativos e sem estoque), paginado.\n\n"
            "Difere do catálogo público que exibe apenas produtos com `is_active=true` "
            "e `available_quantity > 0`."
        ),
    ),
    create=extend_schema(
        tags=_TAG,
        summary="Criar produto",
        description=(
            "Cria um novo produto.\n\n"
            "O estoque é criado automaticamente via signal com `available_quantity=0`. "
            "Use `POST /api/admin/stock/{id}/adjust/` para adicionar unidades."
        ),
    ),
    retrieve=extend_schema(
        tags=_TAG,
        summary="Detalhe do produto",
        description="Retorna todos os campos do produto pelo ID, incluindo FKs de drop e categoria.",
    ),
    update=extend_schema(
        tags=_TAG,
        summary="Atualizar produto (PUT)",
        description="Substituição completa — todos os campos obrigatórios devem ser enviados.",
    ),
    partial_update=extend_schema(exclude=True),
    destroy=extend_schema(
        tags=_TAG,
        summary="Remover produto",
        description=(
            "Remove permanentemente o produto, seu estoque e todas as movimentações associadas."
        ),
    ),
)
class AdminProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    http_method_names = ["get", "post", "put", "delete", "head", "options"]
    queryset = Product.objects.select_related("category", "drop").all()
    serializer_class = AdminProductSerializer


@extend_schema_view(
    create=extend_schema(
        tags=_TAG,
        summary="Upload de imagem",
        description=(
            "Envia uma imagem para um produto via `multipart/form-data`.\n\n"
            "**Campos:** `product` (ID), `file` (imagem), `display_order` (inteiro), "
            "`description` (texto livre).\n\n"
            "**Formatos aceitos:** JPEG, PNG, WebP — máximo 10 MB.\n\n"
            "`mime_type` e `size_bytes` são preenchidos automaticamente."
        ),
    ),
    destroy=extend_schema(
        tags=_TAG,
        summary="Remover imagem",
        description="Remove permanentemente a imagem pelo ID. O arquivo no storage também é excluído.",
    ),
)
class AdminProductImageViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]
    queryset = ProductImage.objects.all()
    serializer_class = AdminProductImageSerializer


@extend_schema_view(
    list=extend_schema(
        tags=_TAG,
        summary="Listar variações",
        description="Lista todas as variações de produto (incluindo inativas), paginado.",
    ),
    create=extend_schema(
        tags=_TAG,
        summary="Criar variação",
        description=(
            "Cria uma variação de tamanho para um produto.\n\n"
            "O estoque é criado automaticamente com `available_quantity=0`. "
            "Use `POST /api/admin/stock/{variation_id}/adjust/` para adicionar unidades."
        ),
    ),
    retrieve=extend_schema(
        tags=_TAG,
        summary="Detalhe da variação",
        description="Retorna todos os campos da variação pelo ID.",
    ),
    update=extend_schema(
        tags=_TAG,
        summary="Atualizar variação (PUT)",
        description="Substituição completa — todos os campos obrigatórios devem ser enviados.",
    ),
    partial_update=extend_schema(exclude=True),
    destroy=extend_schema(
        tags=_TAG,
        summary="Remover variação",
        description="Remove permanentemente a variação, seu estoque e todas as movimentações.",
    ),
)
class AdminProductVariationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    http_method_names = ["get", "post", "put", "delete", "head", "options"]
    queryset = ProductVariation.objects.select_related("product").all()
    serializer_class = AdminProductVariationSerializer
