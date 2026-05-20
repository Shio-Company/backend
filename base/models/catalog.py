import logging
import mimetypes

from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from base.models.shared import TimestampedModel
from base.validators import validate_max_image_size

logger = logging.getLogger(__name__)


class DropManager(models.Manager):
    def active_now(self):
        """Drops publicáveis no momento: ativos e com launch_date no passado."""
        return self.filter(is_active=True, launch_date__lte=timezone.now())


class Drop(TimestampedModel):
    """Lançamento limitado (Aggregate Root)."""

    name = models.CharField(max_length=100, verbose_name="nome")
    slug = models.SlugField(unique=True, verbose_name="slug")
    description = models.TextField(blank=True, default="", verbose_name="descrição")
    is_active = models.BooleanField(
        default=False,
        verbose_name="ativo",
        help_text="Operador precisa ativar explicitamente antes do lançamento.",
    )
    cover_image = models.ImageField(
        upload_to="drops/%Y/%m/",
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
            validate_max_image_size,
        ],
        verbose_name="imagem de capa",
        help_text="Banner principal do drop. JPG/JPEG/PNG/WEBP, máximo 10 MB.",
    )
    launch_date = models.DateTimeField(
        verbose_name="data de lançamento",
        help_text="Data e hora de liberação pública do drop.",
    )

    objects = DropManager()

    class Meta:
        verbose_name = "drop"
        verbose_name_plural = "drops"
        ordering = ["-launch_date"]

    def __str__(self):
        return f"{self.name} ({self.slug})"


class Category(TimestampedModel):
    name = models.CharField(max_length=100, verbose_name="nome")
    slug = models.SlugField(unique=True, verbose_name="slug")
    description = models.TextField(blank=True, default="", verbose_name="descrição")
    is_active = models.BooleanField(default=True, verbose_name="ativa")

    class Meta:
        verbose_name = "categoria"
        verbose_name_plural = "categorias"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProductManager(models.Manager):
    def available(self):
        """Produtos publicáveis: ativos, com drop ativo (ou sem drop), e com ao menos uma
        variação ativa com estoque disponível.
        """
        return (
            self.filter(is_active=True)
            .filter(models.Q(drop__isnull=True) | models.Q(drop__is_active=True))
            .filter(variations__is_active=True, variations__stock__available_quantity__gt=0)
            .distinct()
        )


class Product(TimestampedModel):
    drop = models.ForeignKey(
        Drop,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="drop",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="categoria",
    )
    name = models.CharField(max_length=200, verbose_name="nome")
    slug = models.SlugField(unique=True, verbose_name="slug")
    description = models.TextField(verbose_name="descrição")
    regular_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name="preço regular",
    )
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.01)],
        verbose_name="preço promocional",
        help_text="Quando definido, sobrepõe o preço regular.",
    )
    is_active = models.BooleanField(default=True, verbose_name="ativo")
    weight_g = models.PositiveIntegerField(
        verbose_name="peso (g)",
        help_text="Peso em gramas, usado no cálculo de frete.",
    )
    length_cm = models.PositiveSmallIntegerField(
        verbose_name="comprimento (cm)",
        help_text="Comprimento da embalagem em centímetros (frete).",
    )
    width_cm = models.PositiveSmallIntegerField(
        verbose_name="largura (cm)",
        help_text="Largura da embalagem em centímetros (frete).",
    )
    height_cm = models.PositiveSmallIntegerField(
        verbose_name="altura (cm)",
        help_text="Altura da embalagem em centímetros (frete).",
    )

    objects = ProductManager()

    class Meta:
        verbose_name = "produto"
        verbose_name_plural = "produtos"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def current_price(self):
        """Preço efetivo: sale_price se definido, senão regular_price."""
        return self.sale_price or self.regular_price


class SizeChoice(models.TextChoices):
    P = "P", "P"
    M = "M", "M"
    G = "G", "G"
    GG = "GG", "GG"
    UNICO = "ÚNICO", "Único"


class ProductVariation(TimestampedModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variations",
        verbose_name="produto",
    )
    size = models.CharField(
        max_length=5,
        choices=SizeChoice.choices,
        verbose_name="tamanho",
    )
    is_active = models.BooleanField(default=True, verbose_name="ativa")

    class Meta:
        verbose_name = "variação de produto"
        verbose_name_plural = "variações de produto"
        unique_together = [("product", "size")]
        ordering = ["size"]

    def __str__(self):
        return f"{self.product.slug} — {self.size}"


class ProductImage(TimestampedModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="produto",
    )
    file = models.ImageField(
        upload_to="images/%Y/%m/",
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
            validate_max_image_size,
        ],
        verbose_name="arquivo",
        help_text="JPG/JPEG/PNG/WEBP, máximo 10 MB.",
    )
    display_order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="ordem de exibição",
        help_text="Imagens com ordem menor aparecem primeiro.",
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="descrição",
        help_text="Texto alternativo (alt) e legenda.",
    )
    mime_type = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="MIME type",
    )
    size_bytes = models.PositiveIntegerField(
        default=0,
        verbose_name="tamanho (bytes)",
    )

    class Meta:
        verbose_name = "imagem de produto"
        verbose_name_plural = "imagens de produto"
        ordering = ["display_order", "created_at"]

    def __str__(self):
        return f"{self.product.slug} #{self.display_order}"

    def save(self, *args, **kwargs):
        if self.file:
            self.size_bytes = self.file.size
            guessed, _ = mimetypes.guess_type(self.file.name)
            self.mime_type = guessed or ""
        super().save(*args, **kwargs)
