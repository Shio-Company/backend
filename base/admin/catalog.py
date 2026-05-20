from django.contrib import admin

from base.models.catalog import Category, Drop, Product, ProductImage, ProductVariation


class ProductVariationInline(admin.TabularInline):
    model = ProductVariation
    extra = 1
    fields = ("size", "is_active")


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("file", "display_order", "description", "mime_type", "size_bytes")
    readonly_fields = ("mime_type", "size_bytes")


@admin.register(Drop)
class DropAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "launch_date")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("-launch_date",)
    list_per_page = 50
    fields = ("name", "slug", "description", "cover_image", "is_active", "launch_date")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    list_per_page = 50


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "drop", "regular_price", "sale_price", "is_active")
    list_filter = ("is_active", "category", "drop")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductVariationInline, ProductImageInline]
    list_per_page = 50
