import logging

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from base.exceptions import InsufficientStockError
from base.models.catalog import ProductVariation
from base.models.inventory import Stock
from base.serializers.inventory import StockAdjustInputSerializer, StockSerializer
from base.services.inventory import StockService

logger = logging.getLogger(__name__)


class StockAdjustView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Admin - Inventory"],
        summary="Ajustar estoque de uma variação",
        description=(
            "Aplica um delta ao `available_quantity` da variação e registra um `StockMovement`.\n\n"
            "**Regras:**\n"
            "- `quantity > 0` → entrada manual, cria movimento do tipo `IN`\n"
            "- `quantity < 0` → baixa manual, cria movimento do tipo `ADJUSTMENT`\n"
            "- `quantity = 0` → inválido, retorna `400`\n"
            "- resultado negativo → inviável, retorna `409` sem alterar o estoque\n\n"
            "**Campo `reason`:** texto livre para auditoria (ex.: `'reposição'`, `'avaria'`). "
            "Fica gravado no `StockMovement` junto ao usuário que realizou a operação.\n\n"
            "A operação é atômica — usa `SELECT FOR UPDATE` para evitar race conditions."
        ),
        request=StockAdjustInputSerializer,
        responses={
            200: OpenApiResponse(
                response=StockSerializer,
                description="Estoque atualizado com sucesso.",
                examples=[
                    OpenApiExample(
                        name="Entrada de 10 unidades",
                        value={
                            "id": 1,
                            "variation": "camiseta-shio-basic — M",
                            "available_quantity": 40,
                            "reserved_quantity": 0,
                            "minimum_quantity": 5,
                            "last_movement_at": "2026-05-20T13:00:00Z",
                            "updated_at": "2026-05-20T13:00:00Z",
                        },
                        response_only=True,
                        status_codes=["200"],
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Payload inválido — `quantity` é zero ou campo obrigatório ausente.",
                examples=[
                    OpenApiExample(
                        name="quantity zero",
                        value={"detail": "quantity deve ser diferente de zero."},
                        response_only=True,
                        status_codes=["400"],
                    )
                ],
            ),
            401: OpenApiResponse(description="Não autenticado — access token ausente ou inválido."),
            403: OpenApiResponse(description="Acesso negado — requer `is_staff=true`."),
            404: OpenApiResponse(description="Variação não encontrada."),
            409: OpenApiResponse(
                description="Ajuste inviável — resultado seria negativo.",
                examples=[
                    OpenApiExample(
                        name="Estoque insuficiente",
                        value={"detail": "Ajuste inviável: resultado seria -5 (atual=2)"},
                        response_only=True,
                        status_codes=["409"],
                    )
                ],
            ),
        },
        examples=[
            OpenApiExample(
                name="Entrada de estoque (+10)",
                value={"quantity": 10, "reason": "reposição"},
                request_only=True,
            ),
            OpenApiExample(
                name="Baixa por avaria (-3)",
                value={"quantity": -3, "reason": "avaria"},
                request_only=True,
            ),
        ],
    )
    def post(self, request, variation_id):
        variation = get_object_or_404(ProductVariation, pk=variation_id)
        data = StockAdjustInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            StockService.adjust(
                variation,
                delta=data.validated_data["quantity"],
                reason=data.validated_data["reason"],
                user=request.user,
            )
        except InsufficientStockError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        stock = Stock.objects.get(variation=variation)
        return Response(StockSerializer(stock).data, status=status.HTTP_200_OK)
