import logging

from django.db import transaction
from django.utils import timezone

from base.exceptions import InsufficientStockError
from base.models.inventory import Stock, StockMovement

logger = logging.getLogger(__name__)

_STOCK_UPDATE_FIELDS = [
    "available_quantity",
    "reserved_quantity",
    "last_movement_at",
    "updated_at",
]


class StockService:
    """Operações atômicas sobre `Stock`. Cada operação grava um `StockMovement`."""

    @staticmethod
    def _locked_stock(variation):
        return Stock.objects.select_for_update().get(variation=variation)

    @classmethod
    def reserve(cls, variation, qty, *, reason="cart", user=None):
        """Move `qty` de `available_quantity` para `reserved_quantity`. Cria RESERVE."""
        if qty <= 0:
            raise ValueError("qty deve ser positivo")
        with transaction.atomic():
            stock = cls._locked_stock(variation)
            if stock.available_quantity < qty:
                raise InsufficientStockError(
                    f"Insuficiente para reservar: pedido={qty}, "
                    f"disponível={stock.available_quantity}"
                )
            stock.available_quantity -= qty
            stock.reserved_quantity += qty
            stock.last_movement_at = timezone.now()
            stock.save(update_fields=_STOCK_UPDATE_FIELDS)
            StockMovement.objects.create(
                variation=variation,
                movement_type=StockMovement.MovementType.RESERVE,
                quantity=qty,
                reason=reason,
                created_by=user,
            )
            logger.info("RESERVE qty=%s variation=%s reason=%s", qty, variation, reason)

    @classmethod
    def release(cls, variation, qty, *, reason="cart_released", user=None):
        """Move `qty` de `reserved_quantity` de volta para `available_quantity`. Cria RELEASE."""
        if qty <= 0:
            raise ValueError("qty deve ser positivo")
        with transaction.atomic():
            stock = cls._locked_stock(variation)
            if stock.reserved_quantity < qty:
                raise InsufficientStockError(
                    f"Insuficiente para liberar: pedido={qty}, "
                    f"reservado={stock.reserved_quantity}"
                )
            stock.reserved_quantity -= qty
            stock.available_quantity += qty
            stock.last_movement_at = timezone.now()
            stock.save(update_fields=_STOCK_UPDATE_FIELDS)
            StockMovement.objects.create(
                variation=variation,
                movement_type=StockMovement.MovementType.RELEASE,
                quantity=qty,
                reason=reason,
                created_by=user,
            )
            logger.info("RELEASE qty=%s variation=%s reason=%s", qty, variation, reason)

    @classmethod
    def commit(cls, variation, qty, *, reason="order", user=None):
        """Confirma a saída: diminui apenas `reserved_quantity`. Cria OUT."""
        if qty <= 0:
            raise ValueError("qty deve ser positivo")
        with transaction.atomic():
            stock = cls._locked_stock(variation)
            if stock.reserved_quantity < qty:
                raise InsufficientStockError(
                    f"Insuficiente para confirmar: pedido={qty}, "
                    f"reservado={stock.reserved_quantity}"
                )
            stock.reserved_quantity -= qty
            stock.last_movement_at = timezone.now()
            stock.save(update_fields=_STOCK_UPDATE_FIELDS)
            StockMovement.objects.create(
                variation=variation,
                movement_type=StockMovement.MovementType.OUT,
                quantity=qty,
                reason=reason,
                created_by=user,
            )
            logger.info("COMMIT qty=%s variation=%s reason=%s", qty, variation, reason)

    @classmethod
    def adjust(cls, variation, delta, *, reason, user=None):
        """Ajuste manual em `available_quantity` (delta pode ser +/-).

        delta > 0 → cria IN (entrada manual);
        delta < 0 → cria ADJUSTMENT (baixa).
        """
        if delta == 0:
            raise ValueError("delta deve ser diferente de zero")
        with transaction.atomic():
            stock = cls._locked_stock(variation)
            new_available = stock.available_quantity + delta
            if new_available < 0:
                raise InsufficientStockError(
                    f"Ajuste inviável: resultado seria {new_available} "
                    f"(atual={stock.available_quantity})"
                )
            stock.available_quantity = new_available
            stock.last_movement_at = timezone.now()
            stock.save(update_fields=_STOCK_UPDATE_FIELDS)
            movement_type = (
                StockMovement.MovementType.IN
                if delta > 0
                else StockMovement.MovementType.ADJUSTMENT
            )
            StockMovement.objects.create(
                variation=variation,
                movement_type=movement_type,
                quantity=delta,
                reason=reason,
                created_by=user,
            )
            logger.info(
                "ADJUST delta=%s variation=%s type=%s reason=%s",
                delta,
                variation,
                movement_type,
                reason,
            )
