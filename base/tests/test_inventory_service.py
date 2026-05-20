import pytest

from base.services.catalog import InventoryService
from base.tests.factories import ProductFactory


@pytest.mark.django_db
def test_get_summary_counts_only_active_products():
    ProductFactory.create_batch(2, is_active=True)
    ProductFactory(is_active=False)

    summary = InventoryService.get_summary()

    assert summary["total_products"] == 2
    # TODO Task 1.4: passar a refletir Stock real
    assert summary["total_stock"] == 0
    assert summary["low_stock_count"] == 0
