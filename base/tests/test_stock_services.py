import threading

import pytest

from base.exceptions import InsufficientStockError
from base.models.inventory import Stock, StockMovement
from base.services.inventory import StockService
from base.tests.factories import ProductVariationFactory, StockFactory, UserFactory

# ─── reserve ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_reserve_decreases_available_increases_reserved():
    variation = ProductVariationFactory()
    StockFactory(variation=variation, available_quantity=10, reserved_quantity=0)

    StockService.reserve(variation, 3)

    stock = Stock.objects.get(variation=variation)
    assert stock.available_quantity == 7
    assert stock.reserved_quantity == 3
    assert stock.last_movement_at is not None


@pytest.mark.django_db
def test_reserve_creates_stock_movement_with_reason_and_user():
    variation = ProductVariationFactory()
    user = UserFactory()
    StockFactory(variation=variation, available_quantity=10)

    StockService.reserve(variation, 2, reason="cart-test", user=user)

    movement = StockMovement.objects.get(variation=variation)
    assert movement.movement_type == StockMovement.MovementType.RESERVE
    assert movement.quantity == 2
    assert movement.reason == "cart-test"
    assert movement.created_by == user


@pytest.mark.django_db
def test_reserve_raises_insufficient_when_available_low():
    variation = ProductVariationFactory()
    StockFactory(variation=variation, available_quantity=2)

    with pytest.raises(InsufficientStockError):
        StockService.reserve(variation, 5)


@pytest.mark.django_db
def test_reserve_raises_value_error_for_non_positive_qty():
    variation = ProductVariationFactory()
    StockFactory(variation=variation, available_quantity=10)

    with pytest.raises(ValueError):
        StockService.reserve(variation, 0)
    with pytest.raises(ValueError):
        StockService.reserve(variation, -1)


# ─── release ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_release_returns_qty_to_available():
    variation = ProductVariationFactory()
    StockFactory(variation=variation, available_quantity=5, reserved_quantity=3)

    StockService.release(variation, 2)

    stock = Stock.objects.get(variation=variation)
    assert stock.available_quantity == 7
    assert stock.reserved_quantity == 1


@pytest.mark.django_db
def test_release_raises_when_reserved_too_low():
    variation = ProductVariationFactory()
    StockFactory(variation=variation, reserved_quantity=1)

    with pytest.raises(InsufficientStockError):
        StockService.release(variation, 5)


# ─── commit ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_commit_subtracts_from_reserved_only():
    variation = ProductVariationFactory()
    StockFactory(variation=variation, available_quantity=5, reserved_quantity=3)

    StockService.commit(variation, 2)

    stock = Stock.objects.get(variation=variation)
    assert stock.available_quantity == 5  # available NÃO mudou
    assert stock.reserved_quantity == 1


@pytest.mark.django_db
def test_commit_creates_out_movement():
    variation = ProductVariationFactory()
    StockFactory(variation=variation, reserved_quantity=3)

    StockService.commit(variation, 3, reason="order-42")

    movement = StockMovement.objects.get(variation=variation)
    assert movement.movement_type == StockMovement.MovementType.OUT
    assert movement.quantity == 3
    assert movement.reason == "order-42"


@pytest.mark.django_db
def test_commit_raises_when_reserved_too_low():
    variation = ProductVariationFactory()
    StockFactory(variation=variation, reserved_quantity=1)

    with pytest.raises(InsufficientStockError):
        StockService.commit(variation, 5)


# ─── adjust ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_adjust_positive_creates_in_movement():
    variation = ProductVariationFactory()
    StockFactory(variation=variation, available_quantity=10)

    StockService.adjust(variation, 5, reason="restock")

    stock = Stock.objects.get(variation=variation)
    assert stock.available_quantity == 15
    movement = StockMovement.objects.get(variation=variation)
    assert movement.movement_type == StockMovement.MovementType.IN
    assert movement.quantity == 5


@pytest.mark.django_db
def test_adjust_negative_creates_adjustment_movement():
    variation = ProductVariationFactory()
    StockFactory(variation=variation, available_quantity=10)

    StockService.adjust(variation, -3, reason="loss")

    stock = Stock.objects.get(variation=variation)
    assert stock.available_quantity == 7
    movement = StockMovement.objects.get(variation=variation)
    assert movement.movement_type == StockMovement.MovementType.ADJUSTMENT
    assert movement.quantity == -3


@pytest.mark.django_db
def test_adjust_raises_when_result_negative():
    variation = ProductVariationFactory()
    StockFactory(variation=variation, available_quantity=2)

    with pytest.raises(InsufficientStockError):
        StockService.adjust(variation, -5, reason="loss")


@pytest.mark.django_db
def test_adjust_raises_value_error_for_zero_delta():
    variation = ProductVariationFactory()
    StockFactory(variation=variation, available_quantity=10)

    with pytest.raises(ValueError):
        StockService.adjust(variation, 0, reason="noop")


# ─── race condition ───────────────────────────────────────────────────────────


@pytest.mark.django_db(transaction=True)
def test_reserve_race_only_one_thread_succeeds():
    """Dois threads tentam reservar todo o estoque; select_for_update garante que só 1 sucede."""
    variation = ProductVariationFactory()
    StockFactory(variation=variation, available_quantity=5)

    successes, errors = [], []

    def try_reserve():
        try:
            StockService.reserve(variation, 5)
            successes.append(True)
        except InsufficientStockError:
            errors.append(True)

    threads = [threading.Thread(target=try_reserve) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(successes) == 1, "exatamente 1 thread deve ter sucesso"
    assert len(errors) == 1, "exatamente 1 thread deve receber InsufficientStockError"
    stock = Stock.objects.get(variation=variation)
    assert stock.available_quantity == 0
    assert stock.reserved_quantity == 5
