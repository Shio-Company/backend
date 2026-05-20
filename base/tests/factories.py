from decimal import Decimal

import factory
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify

from base.models.catalog import Category, Drop, Product, ProductImage, ProductVariation, SizeChoice
from base.models.inventory import Stock, StockMovement
from base.models.notifications import EmailLog

User = get_user_model()


# ─── authentication ───────────────────────────────────────────────────────────


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.Faker("name", locale="pt_BR")
    google_id = factory.Sequence(lambda n: f"google_id_{n}")
    is_new_user = True
    avatar_url = factory.Faker("image_url")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # Usa create_user para garantir senha não-utilizável (padrão OAuth)
        return model_class.objects.create_user(*args, **kwargs, password=None)


# ─── catalog ──────────────────────────────────────────────────────────────────


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Categoria {n}")
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    description = ""
    is_active = True


class DropFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Drop

    name = factory.Sequence(lambda n: f"Drop {n}")
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    description = ""
    is_active = True
    launch_date = factory.LazyFunction(timezone.now)


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Produto {n}")
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    description = "Descrição do produto"
    category = factory.SubFactory(CategoryFactory)
    drop = None
    regular_price = Decimal("99.90")
    sale_price = None
    is_active = True
    weight_g = 500
    length_cm = 20
    width_cm = 15
    height_cm = 10


class ProductImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductImage

    product = factory.SubFactory(ProductFactory)
    file = factory.django.ImageField(color="blue", format="JPEG")
    display_order = 0
    description = ""


# ─── inventory ────────────────────────────────────────────────────────────────


class ProductVariationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductVariation

    product = factory.SubFactory(ProductFactory)
    size = SizeChoice.M
    is_active = True


class StockFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Stock

    variation = factory.SubFactory(ProductVariationFactory)
    available_quantity = 10
    reserved_quantity = 0
    minimum_quantity = 5

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # O signal post_save já criou um Stock(0,0,5) para a variation.
        # Atualizamos esse stock em vez de criar um segundo (OneToOne).
        variation = kwargs.pop("variation")
        stock, _ = model_class.objects.update_or_create(variation=variation, defaults=kwargs)
        return stock


class StockMovementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StockMovement

    variation = factory.SubFactory(ProductVariationFactory)
    movement_type = StockMovement.MovementType.IN
    quantity = 1
    reason = ""
    created_by = None


# ─── notifications ────────────────────────────────────────────────────────────


class EmailLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EmailLog

    recipient_email = factory.Sequence(lambda n: f"user{n}@example.com")
    template_name = EmailLog.Template.WELCOME
    subject = "Bem-vindo à Shio!"
    context = factory.LazyAttribute(lambda o: {"name": "Teste", "email": o.recipient_email})
    status = EmailLog.Status.PENDING
    provider = "ConsoleEmailBackend"
