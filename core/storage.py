from whitenoise.storage import CompressedManifestStaticFilesStorage


class StaticFilesStorage(CompressedManifestStaticFilesStorage):
    # O Django admin referencia arquivos CSS de forma que o WhiteNoise não consegue
    # resolver durante o collectstatic. Desabilitando a validação estrita evita o erro
    # sem perder compressão ou cache-busting.
    manifest_strict = False
