from django.core.exceptions import ValidationError

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def validate_max_image_size(file) -> None:
    """Rejeita arquivos maiores que 10 MB."""
    if file.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError(
            f"Arquivo excede o limite de {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)} MB.",
            code="file_too_large",
        )
