import pytest
from django.test import Client
from django.urls import reverse

from base.models.inventory import StockMovement
from base.tests.factories import StockFactory, UserFactory

pytestmark = pytest.mark.django_db

CHANGELIST_URL = reverse("admin:base_stock_changelist")


@pytest.fixture
def client_admin():
    admin = UserFactory.create(is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(admin)
    return client


def test_ajustar_estoque_intermediate_page_renders(client_admin):
    """POST da action sem 'apply' mostra a página de confirmação (200 + form)."""
    stock = StockFactory(available_quantity=10)

    response = client_admin.post(
        CHANGELIST_URL,
        data={"action": "ajustar_estoque", "_selected_action": [str(stock.pk)]},
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert 'name="delta"' in content
    assert 'name="reason"' in content
    assert 'name="apply"' in content


def test_ajustar_estoque_apply_positive_increases_and_logs_in(client_admin):
    """apply com delta=+10 aumenta available_quantity e cria StockMovement IN."""
    stock = StockFactory(available_quantity=10)

    response = client_admin.post(
        CHANGELIST_URL,
        data={
            "action": "ajustar_estoque",
            "_selected_action": [str(stock.pk)],
            "apply": "1",
            "delta": "10",
            "reason": "restock",
        },
        follow=True,
    )

    assert response.status_code == 200
    stock.refresh_from_db()
    assert stock.available_quantity == 20
    movement = StockMovement.objects.get(variation=stock.variation, reason="restock")
    assert movement.movement_type == StockMovement.MovementType.IN
    assert movement.quantity == 10
    assert movement.created_by_id is not None


def test_ajustar_estoque_apply_negative_creates_adjustment(client_admin):
    """delta negativo válido cria movimento ADJUSTMENT e diminui o disponível."""
    stock = StockFactory(available_quantity=10)

    client_admin.post(
        CHANGELIST_URL,
        data={
            "action": "ajustar_estoque",
            "_selected_action": [str(stock.pk)],
            "apply": "1",
            "delta": "-4",
            "reason": "perda",
        },
        follow=True,
    )

    stock.refresh_from_db()
    assert stock.available_quantity == 6
    movement = StockMovement.objects.get(variation=stock.variation, reason="perda")
    assert movement.movement_type == StockMovement.MovementType.ADJUSTMENT
    assert movement.quantity == -4


def test_ajustar_estoque_insufficient_does_not_change_stock(client_admin):
    """delta que tornaria o disponível negativo é reportado e não altera o estoque."""
    stock = StockFactory(available_quantity=3)

    client_admin.post(
        CHANGELIST_URL,
        data={
            "action": "ajustar_estoque",
            "_selected_action": [str(stock.pk)],
            "apply": "1",
            "delta": "-10",
            "reason": "baixa-invalida",
        },
        follow=True,
    )

    stock.refresh_from_db()
    assert stock.available_quantity == 3
    assert not StockMovement.objects.filter(reason="baixa-invalida").exists()


def test_stock_admin_add_is_forbidden(client_admin):
    """Stock não pode ser criado manualmente (criado pelo signal)."""
    add_url = reverse("admin:base_stock_add")
    response = client_admin.get(add_url)
    assert response.status_code == 403
