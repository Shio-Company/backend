import logging

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from base.models.catalog import Category, Drop, Product, ProductImage, ProductVariation

logger = logging.getLogger(__name__)


class InventorySummarySerializer(serializers.Serializer):
    total_products = serializers.IntegerField(help_text="Total de produtos ativos no catálogo.")
    total_stock = serializers.IntegerField(
        help_text="Soma total de unidades em estoque (todas as variações)."
    )
    low_stock_count = serializers.IntegerField(
        help_text="Produtos ativos com estoque total ≤ 5 unidades."
    )


class ProductVariationSerializer(serializers.ModelSerializer):
    stock_available = serializers.SerializerMethodField(
        help_text="Unidades disponíveis para esta variação."
    )

    class Meta:
        model = ProductVariation
        fields = ["id", "size", "is_active", "stock_available"]
        read_only_fields = fields

    def get_stock_available(self, obj) -> int:
        stock = getattr(obj, "stock", None)
        return stock.available_quantity if stock else 0


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "file", "display_order", "description", "mime_type", "size_bytes"]
        read_only_fields = fields


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "is_active"]
        read_only_fields = fields


class DropListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drop
        fields = ["id", "name", "slug", "description", "is_active", "launch_date", "cover_image", "created_at"]
        read_only_fields = fields


class ProductListSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    drop = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    current_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
        help_text="Preço efetivo (sale_price se definido, senão regular_price).",
    )
    cover_image = serializers.SerializerMethodField(
        help_text="Imagem de capa (menor display_order). Null se o produto não tiver imagens."
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "category",
            "drop",
            "regular_price",
            "sale_price",
            "current_price",
            "is_active",
            "cover_image",
        ]
        read_only_fields = fields

    @extend_schema_field(ProductImageSerializer)
    def get_cover_image(self, obj):
        images = obj.images.all()
        if not images:
            return None
        cover = min(images, key=lambda img: img.display_order)
        return ProductImageSerializer(cover, context=self.context).data


class DropDetailSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField(
        help_text="Produtos ativos pertencentes a este drop."
    )

    class Meta:
        model = Drop
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "is_active",
            "launch_date",
            "cover_image",
            "created_at",
            "products",
        ]
        read_only_fields = fields

    @extend_schema_field(ProductListSerializer(many=True))
    def get_products(self, obj):
        produtos = obj.products.filter(is_active=True)
        return ProductListSerializer(produtos, many=True, context=self.context).data


class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    drop = DropListSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variations = ProductVariationSerializer(many=True, read_only=True)
    current_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
        help_text="Preço efetivo (sale_price se definido, senão regular_price).",
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "drop",
            "category",
            "name",
            "slug",
            "description",
            "regular_price",
            "sale_price",
            "current_price",
            "is_active",
            "weight_g",
            "length_cm",
            "width_cm",
            "height_cm",
            "images",
            "variations",
            "created_at",
        ]
        read_only_fields = fields


# ─── Admin (CRUD, fields completos e graváveis) ───────────────────────────────


class AdminDropSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drop
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "is_active",
            "launch_date",
            "cover_image",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AdminCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "is_active"]
        read_only_fields = ["id"]


class AdminProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "drop",
            "category",
            "name",
            "slug",
            "description",
            "regular_price",
            "sale_price",
            "is_active",
            "weight_g",
            "length_cm",
            "width_cm",
            "height_cm",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AdminProductVariationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariation
        fields = ["id", "product", "size", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class AdminProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = [
            "id",
            "product",
            "file",
            "display_order",
            "description",
            "mime_type",
            "size_bytes",
        ]
        read_only_fields = ["id", "mime_type", "size_bytes"]
