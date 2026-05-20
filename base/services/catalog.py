import logging

from django.db.models import F, Sum

from base.models.catalog import Product
from base.models.inventory import Stock

logger = logging.getLogger(__name__)


class InventoryService:
    @staticmethod
    def get_summary() -> dict:
        total_products = Product.objects.filter(is_active=True).count()
        total_stock = (
            Stock.objects.filter(variation__product__is_active=True).aggregate(
                total=Sum("available_quantity")
            )["total"]
            or 0
        )
        low_stock_count = Stock.objects.filter(
            variation__product__is_active=True,
            available_quantity__lte=F("minimum_quantity"),
        ).count()

        logger.info("InventoryService.get_summary chamado.")
        return {
            "total_products": total_products,
            "total_stock": total_stock,
            "low_stock_count": low_stock_count,
        }
