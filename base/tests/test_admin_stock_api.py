import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from base.models.inventory import StockMovement
from base.tests.factories import ProductVariationFactory, StockFactory, UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client():
    client = APIClient()
    client.force_authenticate(user=UserFactory.create(is_staff=True, is_superuser=True))
    return client


def _url(variation_id):
    return reverse("base:admin-stock-adjust", kwargs={"variation_id": variation_id})


def test_admin_adjust_positive_increases_and_logs_in(admin_client):
    variation = ProductVariationFactory()
    StockFactory(variation=variation, available_quantity=10)

    response = admin_client.post(
        _url(variation.pk), {"quantity": 10, "reason": "reposição"}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["available_quantity"] == 20
    movement = StockMovement.objects.get(variation=variation, reason="reposição")
    assert movement.movement_type == StockMovement.MovementType.IN
    assert movement.created_by_id is not None


def test_admin_adjust_insufficient_returns_409(admin_client):
    variation = ProductVariationFactory()
    StockFactory(variation=variation, available_quantity=3)

    response = admin_client.post(
        _url(variation.pk), {"quantity": -10, "reason": "baixa"}, format="json"
    )

    assert response.status_code == 409
    variation.stock.refresh_from_db()
    assert variation.stock.available_quantity == 3
    assert not StockMovement.objects.filter(reason="baixa").exists()


def test_admin_adjust_zero_returns_400(admin_client):
    variation = ProductVariationFactory()
    StockFactory(variation=variation, available_quantity=5)
    response = admin_client.post(_url(variation.pk), {"quantity": 0, "reason": "x"}, format="json")
    assert response.status_code == 400


def test_adjust_variation_not_found_returns_404(admin_client):
    response = admin_client.post(_url(999999), {"quantity": 1, "reason": "x"}, format="json")
    assert response.status_code == 404


def test_non_admin_adjust_forbidden():
    variation = ProductVariationFactory()
    client = APIClient()
    client.force_authenticate(user=UserFactory.create())
    response = client.post(_url(variation.pk), {"quantity": 1, "reason": "x"}, format="json")
    assert response.status_code == 403


def test_anonymous_adjust_unauthorized():
    variation = ProductVariationFactory()
    response = APIClient().post(_url(variation.pk), {"quantity": 1, "reason": "x"}, format="json")
    assert response.status_code == 401
