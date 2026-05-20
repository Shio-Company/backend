from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from base.models.catalog import Drop, Product
from base.tests.factories import DropFactory, ProductFactory, ProductVariationFactory, StockFactory

# ─── Drop.active_now() ───────────────────────────────────────────────────────


@pytest.mark.django_db
def test_drop_active_now_includes_active_past_launch():
    drop = DropFactory(is_active=True, launch_date=timezone.now() - timedelta(hours=1))
    assert drop in Drop.objects.active_now()


@pytest.mark.django_db
def test_drop_active_now_excludes_future_launch():
    drop = DropFactory(is_active=True, launch_date=timezone.now() + timedelta(days=7))
    assert drop not in Drop.objects.active_now()


@pytest.mark.django_db
def test_drop_active_now_excludes_inactive():
    drop = DropFactory(is_active=False, launch_date=timezone.now() - timedelta(hours=1))
    assert drop not in Drop.objects.active_now()


# ─── Product.available() ─────────────────────────────────────────────────────


@pytest.mark.django_db
def test_product_available_excludes_inactive():
    product = ProductFactory(is_active=False)
    assert product not in Product.objects.available()


@pytest.mark.django_db
def test_product_available_includes_no_drop():
    product = ProductFactory(is_active=True, drop=None)
    variation = ProductVariationFactory(product=product)
    StockFactory(variation=variation, available_quantity=5)
    assert product in Product.objects.available()


@pytest.mark.django_db
def test_product_available_includes_active_drop():
    drop = DropFactory(is_active=True, launch_date=timezone.now() - timedelta(hours=1))
    product = ProductFactory(is_active=True, drop=drop)
    variation = ProductVariationFactory(product=product)
    StockFactory(variation=variation, available_quantity=5)
    assert product in Product.objects.available()


@pytest.mark.django_db
def test_product_available_excludes_inactive_drop():
    drop = DropFactory(is_active=False, launch_date=timezone.now() - timedelta(hours=1))
    product = ProductFactory(is_active=True, drop=drop)
    assert product not in Product.objects.available()


# ─── Product.current_price ───────────────────────────────────────────────────


@pytest.mark.django_db
def test_current_price_returns_sale_when_set():
    product = ProductFactory(regular_price=Decimal("99.90"), sale_price=Decimal("49.90"))
    assert product.current_price == Decimal("49.90")


@pytest.mark.django_db
def test_current_price_returns_regular_when_no_sale():
    product = ProductFactory(regular_price=Decimal("99.90"), sale_price=None)
    assert product.current_price == Decimal("99.90")
