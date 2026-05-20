from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from base.tests.factories import (
    CategoryFactory,
    DropFactory,
    ProductFactory,
    ProductImageFactory,
    ProductVariationFactory,
    StockFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()  # sem autenticação — catálogo é público


def _product_with_stock(available_quantity=10, **product_kwargs):
    """Cria Product + Variation(M) + Stock para aparecer no catálogo público."""
    product = ProductFactory(is_active=True, **product_kwargs)
    variation = ProductVariationFactory(product=product)
    StockFactory(variation=variation, available_quantity=available_quantity)
    return product


# ─── drops ───────────────────────────────────────────────────────────────────


def test_list_drops_public_paginated_only_active_now(client):
    ativo = DropFactory(is_active=True, launch_date=timezone.now() - timedelta(hours=1))
    DropFactory(is_active=True, launch_date=timezone.now() + timedelta(days=1))  # futuro
    DropFactory(is_active=False, launch_date=timezone.now() - timedelta(hours=1))  # inativo

    response = client.get(reverse("base:drop-list"))

    assert response.status_code == 200
    body = response.json()
    assert {"count", "next", "previous", "results"} <= set(body)
    slugs = [d["slug"] for d in body["results"]]
    assert slugs == [ativo.slug]


def test_retrieve_drop_by_slug_includes_active_products(client):
    drop = DropFactory(is_active=True, launch_date=timezone.now() - timedelta(hours=1))
    active_product = ProductFactory(drop=drop, is_active=True)
    ProductFactory(drop=drop, is_active=False)  # inativo — não aparece

    response = client.get(reverse("base:drop-detail", kwargs={"slug": drop.slug}))

    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == drop.slug
    assert len(body["products"]) == 1
    assert body["products"][0]["slug"] == active_product.slug


# ─── categories ──────────────────────────────────────────────────────────────


def test_list_categories_public(client):
    CategoryFactory(is_active=True)
    response = client.get(reverse("base:category-list"))
    assert response.status_code == 200
    assert response.json()["count"] == 1


# ─── products ──────────────────────────────────────────────────────────────--


def test_list_products_excludes_unavailable(client):
    disponivel = _product_with_stock(available_quantity=10)
    ProductFactory(is_active=False)  # sem variação + inativo

    response = client.get(reverse("base:product-list"))

    assert response.status_code == 200
    slugs = [p["slug"] for p in response.json()["results"]]
    assert slugs == [disponivel.slug]


def test_list_products_excludes_out_of_stock(client):
    """Produto com variação mas estoque zero não aparece no catálogo público."""
    product = ProductFactory(is_active=True)
    variation = ProductVariationFactory(product=product)
    StockFactory(variation=variation, available_quantity=0)

    response = client.get(reverse("base:product-list"))

    slugs = [p["slug"] for p in response.json()["results"]]
    assert product.slug not in slugs


def test_filter_products_by_drop_and_category_slug(client):
    drop = DropFactory(is_active=True, launch_date=timezone.now() - timedelta(hours=1))
    cat = CategoryFactory()
    alvo = _product_with_stock(drop=drop, category=cat)
    _product_with_stock()  # outro drop/categoria

    url = reverse("base:product-list")
    response = client.get(url, {"drop": drop.slug, "category": cat.slug})

    assert response.status_code == 200
    slugs = [p["slug"] for p in response.json()["results"]]
    assert slugs == [alvo.slug]


def test_search_products_by_name(client):
    alvo = _product_with_stock(name="Camiseta Nike Drop")
    _product_with_stock(name="Boné Adidas")

    response = client.get(reverse("base:product-list"), {"search": "nike"})

    assert response.status_code == 200
    slugs = [p["slug"] for p in response.json()["results"]]
    assert slugs == [alvo.slug]


def test_retrieve_product_detail_has_images_and_variations(client):
    product = ProductFactory(is_active=True)
    ProductImageFactory(product=product)
    variation = ProductVariationFactory(product=product)
    StockFactory(variation=variation, available_quantity=7)

    response = client.get(reverse("base:product-detail", kwargs={"slug": product.slug}))

    assert response.status_code == 200
    body = response.json()
    assert len(body["images"]) == 1
    assert "current_price" in body
    assert len(body["variations"]) == 1
    assert body["variations"][0]["size"] == variation.size
    assert body["variations"][0]["stock_available"] == 7


# ─── público sem autenticação ──────────────────────────────────────────────--


def test_catalog_endpoints_are_public(client):
    drop = DropFactory(is_active=True, launch_date=timezone.now() - timedelta(hours=1))
    product = _product_with_stock()

    # nenhuma credencial enviada
    assert client.get(reverse("base:drop-list")).status_code == 200
    assert client.get(reverse("base:category-list")).status_code == 200
    assert client.get(reverse("base:product-list")).status_code == 200
    assert client.get(reverse("base:drop-detail", kwargs={"slug": drop.slug})).status_code == 200
    assert (
        client.get(reverse("base:product-detail", kwargs={"slug": product.slug})).status_code
        == 200
    )
