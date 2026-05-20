from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from base.models.catalog import Drop, ProductImage
from base.tests.factories import ProductFactory, UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client():
    client = APIClient()
    client.force_authenticate(user=UserFactory.create(is_staff=True, is_superuser=True))
    return client


@pytest.fixture
def user_client():
    client = APIClient()
    client.force_authenticate(user=UserFactory.create())
    return client


def _jpeg_upload():
    buf = BytesIO()
    Image.new("RGB", (10, 10), "blue").save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile("t.jpg", buf.read(), content_type="image/jpeg")


# ─── CRUD admin ───────────────────────────────────────────────────────────────


def test_admin_creates_drop(admin_client):
    payload = {
        "name": "Drop X",
        "slug": "drop-x",
        "description": "",
        "is_active": True,
        "launch_date": "2026-01-01T00:00:00Z",
    }
    response = admin_client.post(reverse("base:admin-drop-list"), payload, format="json")
    assert response.status_code == 201
    assert Drop.objects.filter(slug="drop-x").exists()


def test_admin_updates_and_deletes_product(admin_client):
    product = ProductFactory(is_active=True)
    detail = reverse("base:admin-product-detail", kwargs={"pk": product.pk})

    payload = {
        "name": "Novo Nome",
        "slug": product.slug,
        "description": product.description,
        "regular_price": str(product.regular_price),
        "sale_price": None,
        "is_active": product.is_active,
        "weight_g": product.weight_g,
        "length_cm": product.length_cm,
        "width_cm": product.width_cm,
        "height_cm": product.height_cm,
        "drop": product.drop_id,
        "category": product.category_id,
    }
    put = admin_client.put(detail, payload, format="json")
    assert put.status_code == 200
    product.refresh_from_db()
    assert product.name == "Novo Nome"

    delete = admin_client.delete(detail)
    assert delete.status_code == 204


def test_admin_list_includes_inactive(admin_client):
    ProductFactory(is_active=False)
    response = admin_client.get(reverse("base:admin-product-list"))
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_admin_uploads_product_image(admin_client, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    product = ProductFactory(is_active=True)
    response = admin_client.post(
        reverse("base:admin-product-image-list"),
        {"product": product.pk, "file": _jpeg_upload(), "display_order": 0, "description": "capa"},
        format="multipart",
    )
    assert response.status_code == 201
    assert ProductImage.objects.filter(product=product).count() == 1


# ─── permissões ──────────────────────────────────────────────────────────────


def test_non_admin_cannot_create_drop(user_client):
    response = user_client.post(reverse("base:admin-drop-list"), {}, format="json")
    assert response.status_code == 403


def test_anonymous_cannot_create_drop():
    response = APIClient().post(reverse("base:admin-drop-list"), {}, format="json")
    assert response.status_code == 401
