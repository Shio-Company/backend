import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from base.models.catalog import ProductVariation
from base.models.inventory import Stock

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ProductVariation)
def create_stock_for_variation(sender, instance, created, **kwargs):
    """Garante o Stock 1:1 ao criar uma ProductVariation nova (idempotente)."""
    if not created:
        return
    _, was_created = Stock.objects.get_or_create(variation=instance)
    if was_created:
        logger.info("Stock criado automaticamente para variação %s", instance)
