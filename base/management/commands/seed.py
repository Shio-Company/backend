from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from base.models.catalog import Category, Drop, Product, ProductVariation, SizeChoice
from base.services.inventory import StockService


class Command(BaseCommand):
    help = "Popula o banco com dados de exemplo. Use --reset para limpar antes de popular."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Apaga todos os dados de catálogo antes de popular.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            Product.objects.all().delete()
            Drop.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.WARNING("  Dados apagados."))
        self._seed_categories()
        self._seed_drops()
        self._seed_products()
        self.stdout.write(self.style.SUCCESS("Seed concluído."))

    def _seed_categories(self):
        dados = [
            ("Tops", "Camisetas, hoodies e jaquetas."),
            ("Bottoms", "Calças, shorts e saias."),
            ("Acessórios", "Bonés, meias e outros."),
        ]
        for nome, desc in dados:
            cat, created = Category.objects.get_or_create(
                slug=slugify(nome),
                defaults={"name": nome, "description": desc, "is_active": True},
            )
            if created:
                self.stdout.write(f"  Categoria criada: {cat.name}")

    def _seed_drops(self):
        drop, created = Drop.objects.get_or_create(
            slug="drop-001",
            defaults={
                "name": "Drop 001",
                "description": "Primeira coleção da Shio — peças limitadas.",
                "is_active": True,
                "launch_date": timezone.now(),
            },
        )
        if created:
            self.stdout.write(f"  Drop criado: {drop.name}")

    def _seed_products(self):
        drop = Drop.objects.get(slug="drop-001")
        tops = Category.objects.get(slug="tops")
        bottoms = Category.objects.get(slug="bottoms")
        acessorios = Category.objects.get(slug="acessorios")

        # sizes: list de (SizeChoice, qty)
        roupas_sizes = [
            (SizeChoice.P, 8),
            (SizeChoice.M, 12),
            (SizeChoice.G, 12),
            (SizeChoice.GG, 8),
        ]
        unico_size = [(SizeChoice.UNICO, 50)]

        produtos = [
            {
                "name": "Camiseta Shio Basic",
                "slug": "camiseta-shio-basic",
                "category": tops,
                "description": "Camiseta oversized em algodão 100%.",
                "regular_price": "189.90",
                "sale_price": None,
                "weight_g": 250,
                "length_cm": 35,
                "width_cm": 28,
                "height_cm": 2,
                "sizes": roupas_sizes,
            },
            {
                "name": "Hoodie Shio Dropped",
                "slug": "hoodie-shio-dropped",
                "category": tops,
                "description": "Moletom pesado com bordado frontal.",
                "regular_price": "349.90",
                "sale_price": "299.90",
                "weight_g": 600,
                "length_cm": 40,
                "width_cm": 35,
                "height_cm": 5,
                "sizes": roupas_sizes,
            },
            {
                "name": "Calça Cargo Shio",
                "slug": "calca-cargo-shio",
                "category": bottoms,
                "description": "Cargo wide-leg com múltiplos bolsos.",
                "regular_price": "279.90",
                "sale_price": None,
                "weight_g": 500,
                "length_cm": 45,
                "width_cm": 30,
                "height_cm": 3,
                "sizes": roupas_sizes,
            },
            {
                "name": "Boné Shio 6-Panel",
                "slug": "bone-shio-6-panel",
                "category": acessorios,
                "description": "Boné estruturado com logo bordado.",
                "regular_price": "129.90",
                "sale_price": "99.90",
                "weight_g": 150,
                "length_cm": 25,
                "width_cm": 20,
                "height_cm": 12,
                "sizes": unico_size,
            },
            {
                "name": "Meia Shio Logo",
                "slug": "meia-shio-logo",
                "category": acessorios,
                "description": "Pack com 3 pares de meias cano médio.",
                "regular_price": "59.90",
                "sale_price": None,
                "weight_g": 80,
                "length_cm": 20,
                "width_cm": 10,
                "height_cm": 3,
                "sizes": unico_size,
            },
        ]

        for dados in produtos:
            sizes = dados.pop("sizes")
            product, created = Product.objects.get_or_create(
                slug=dados["slug"],
                defaults={**dados, "drop": drop, "is_active": True},
            )
            for size, qty in sizes:
                variation, var_created = ProductVariation.objects.get_or_create(
                    product=product,
                    size=size,
                    defaults={"is_active": True},
                )
                # signal já criou Stock com qty=0; ajustar para qty do seed
                StockService.adjust(variation, delta=qty, reason="seed")
            if created:
                size_labels = ", ".join(s.label for s, _ in sizes)
                self.stdout.write(f"  Produto criado: {product.name} (tamanhos: {size_labels})")
