import pytest
from django.db import IntegrityError, transaction

from base.models.inventory import Stock, StockMovement
from base.tests.factories import ProductVariationFactory, StockFactory, StockMovementFactory

# ─── Stock.objects.low_stock() ───────────────────────────────────────────────


@pytest.mark.django_db
def test_low_stock_includes_at_threshold():
    s = StockFactory(available_quantity=5, minimum_quantity=5)
    assert s in Stock.objects.low_stock()


@pytest.mark.django_db
def test_low_stock_includes_below_threshold():
    s = StockFactory(available_quantity=1, minimum_quantity=5)
    assert s in Stock.objects.low_stock()


@pytest.mark.django_db
def test_low_stock_excludes_above_threshold():
    s = StockFactory(available_quantity=10, minimum_quantity=5)
    assert s not in Stock.objects.low_stock()


# ─── Stock — unicidade 1:1 com ProductVariation ───────────────────────────────


@pytest.mark.django_db
def test_stock_one_per_variation_unique():
    variation = ProductVariationFactory()  # signal post_save já cria 1 Stock
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Stock.objects.create(variation=variation)


# ─── StockMovement — ordering e choices ──────────────────────────────────────


@pytest.mark.django_db
def test_stock_movement_default_ordering_desc_by_created_at():
    variation = ProductVariationFactory()
    first = StockMovementFactory(variation=variation)
    second = StockMovementFactory(variation=variation)

    movements = list(StockMovement.objects.all())
    assert movements[0] == second
    assert movements[1] == first


def test_stock_movement_types_choices():
    values = {choice[0] for choice in StockMovement.MovementType.choices}
    assert values == {"IN", "OUT", "RESERVE", "RELEASE", "ADJUSTMENT"}
