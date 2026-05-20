import pytest

from base.models.inventory import Stock
from base.tests.factories import ProductVariationFactory


@pytest.mark.django_db
def test_creating_variation_auto_creates_stock():
    variation = ProductVariationFactory()
    stock = Stock.objects.get(variation=variation)
    assert stock.available_quantity == 0
    assert stock.reserved_quantity == 0
    assert stock.minimum_quantity == 5
    assert Stock.objects.filter(variation=variation).count() == 1


@pytest.mark.django_db
def test_updating_variation_does_not_create_new_stock():
    variation = ProductVariationFactory()
    assert Stock.objects.filter(variation=variation).count() == 1
    variation.is_active = False
    variation.save()
    assert Stock.objects.filter(variation=variation).count() == 1
