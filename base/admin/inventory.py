from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.template.response import TemplateResponse

from base.exceptions import InsufficientStockError
from base.models.inventory import Stock, StockMovement
from base.services.inventory import StockService


class StockAdjustForm(forms.Form):
    """Form da página intermediária de ajuste de estoque (action do admin)."""

    delta = forms.IntegerField(
        label="Variação (delta)",
        help_text="Inteiro com sinal. Positivo = entrada (IN); negativo = ajuste (ADJUSTMENT).",
    )
    reason = forms.CharField(label="Motivo", max_length=255)

    def clean_delta(self):
        delta = self.cleaned_data["delta"]
        if delta == 0:
            raise forms.ValidationError("delta deve ser diferente de zero.")
        return delta


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = (
        "variation",
        "available_quantity",
        "reserved_quantity",
        "minimum_quantity",
        "last_movement_at",
    )
    list_filter = ("variation__product__category", "variation__product__drop")
    search_fields = ("variation__product__name", "variation__product__slug")
    list_per_page = 50
    actions = ("ajustar_estoque",)

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False  # Stock é criado pelo signal post_save em ProductVariation

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Ajustar estoque")
    def ajustar_estoque(self, request, queryset):
        if "apply" in request.POST:
            form = StockAdjustForm(request.POST)
            if form.is_valid():
                delta = form.cleaned_data["delta"]
                reason = form.cleaned_data["reason"]
                ok = 0
                for stock in queryset.select_related("variation"):
                    try:
                        StockService.adjust(stock.variation, delta, reason=reason, user=request.user)
                        ok += 1
                    except (ValueError, InsufficientStockError) as exc:
                        self.message_user(
                            request, f"{stock.variation}: {exc}", level=messages.ERROR
                        )
                if ok:
                    self.message_user(
                        request,
                        f"Estoque ajustado em {ok} variação(ões) (delta={delta:+d}).",
                        level=messages.SUCCESS,
                    )
                return redirect(request.get_full_path())
        else:
            form = StockAdjustForm()

        context = {
            **self.admin_site.each_context(request),
            "title": "Ajustar estoque",
            "stocks": queryset.select_related("variation"),
            "form": form,
            "action_name": "ajustar_estoque",
            "selected": queryset.values_list("pk", flat=True),
            "opts": self.model._meta,
        }
        return TemplateResponse(request, "admin/base/stock_adjust.html", context)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "variation",
        "movement_type",
        "quantity",
        "reason",
        "created_by",
        "created_at",
    )
    list_filter = ("movement_type",)
    search_fields = ("variation__product__name", "variation__product__slug", "reason")
    list_per_page = 50

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
