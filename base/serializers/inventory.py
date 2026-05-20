from rest_framework import serializers

from base.models.inventory import Stock


class StockAdjustInputSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(
        help_text="Delta a aplicar no disponível (pode ser negativo); 0 é inválido."
    )
    reason = serializers.CharField(max_length=255, help_text="Motivo do ajuste (auditoria).")

    def validate_quantity(self, value):
        if value == 0:
            raise serializers.ValidationError("quantity deve ser diferente de zero.")
        return value


class StockSerializer(serializers.ModelSerializer):
    variation = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Stock
        fields = [
            "id",
            "variation",
            "available_quantity",
            "reserved_quantity",
            "minimum_quantity",
            "last_movement_at",
            "updated_at",
        ]
        read_only_fields = fields
