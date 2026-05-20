import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from base.models.catalog import ProductImage
from base.tests.factories import ProductFactory, ProductImageFactory


@pytest.mark.django_db
def test_save_populates_mime_type_and_size_bytes():
    image = ProductImageFactory()
    assert image.mime_type == "image/jpeg"
    assert image.size_bytes > 0


@pytest.mark.django_db
def test_images_ordered_by_display_order():
    product = ProductFactory()
    ProductImageFactory(product=product, display_order=2)
    ProductImageFactory(product=product, display_order=0)
    ProductImageFactory(product=product, display_order=1)

    orders = list(product.images.values_list("display_order", flat=True))
    assert orders == [0, 1, 2]


@pytest.mark.django_db
def test_validator_rejects_invalid_extension():
    product = ProductFactory()
    bad = SimpleUploadedFile("nota.txt", b"hello world", content_type="text/plain")
    image = ProductImage(product=product, file=bad)

    with pytest.raises(ValidationError):
        image.full_clean()


@pytest.mark.django_db
def test_validator_rejects_oversized_file():
    product = ProductFactory()
    oversized = SimpleUploadedFile(
        "big.jpg",
        b"x" * (11 * 1024 * 1024),
        content_type="image/jpeg",
    )
    image = ProductImage(product=product, file=oversized)

    with pytest.raises(ValidationError):
        image.full_clean()
