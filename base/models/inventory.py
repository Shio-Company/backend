import logging

from django.conf import settings
from django.db import models

from base.models.catalog import Product, ProductVariation
from base.models.shared import TimestampedModel

logger = logging.getLogger(__name__)


class StockManager(models.Manager):
    def low_stock(self):
        """Estoques com available_quantity <= minimum_quantity."""
        return self.filter(available_quantity__lte=models.F("minimum_quantity"))


class Stock(TimestampedModel):
    variation = models.OneToOneField(
        ProductVariation,
        on_delete=models.CASCADE,
        related_name="stock",
        verbose_name="variação",
    )
    available_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name="quantidade disponível",
        help_text="Unidades prontas para venda imediata.",
    )
    reserved_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name="quantidade reservada",
        help_text="Unidades em carrinhos ativos (aguardando checkout).",
    )
    minimum_quantity = models.PositiveIntegerField(
        default=5,
        verbose_name="quantidade mínima",
        help_text="Limiar para alerta de estoque baixo.",
    )
    last_movement_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="última movimentação em",
    )

    objects = StockManager()

    class Meta:
        verbose_name = "estoque"
        verbose_name_plural = "estoques"
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["available_quantity"])]

    def __str__(self):
        return f"Estoque de {self.variation}: {self.available_quantity}"


class StockMovement(TimestampedModel):
    class MovementType(models.TextChoices):
        IN = "IN", "Entrada"
        OUT = "OUT", "Saída"
        RESERVE = "RESERVE", "Reserva"
        RELEASE = "RELEASE", "Liberação"
        ADJUSTMENT = "ADJUSTMENT", "Ajuste"

    variation = models.ForeignKey(
        ProductVariation,
        on_delete=models.CASCADE,
        related_name="stock_movements",
        verbose_name="variação",
    )
    movement_type = models.CharField(
        max_length=10,
        choices=MovementType.choices,
        verbose_name="tipo",
    )
    quantity = models.IntegerField(
        verbose_name="quantidade",
        help_text="Pode ser negativo em ADJUSTMENT.",
    )
    reason = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="motivo",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements",
        verbose_name="criado por",
    )

    class Meta:
        verbose_name = "movimento de estoque"
        verbose_name_plural = "movimentos de estoque"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["variation", "created_at"])]

    def __str__(self):
        return f"{self.movement_type} {self.quantity} - {self.variation}"
