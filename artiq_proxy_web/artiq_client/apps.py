from django.apps import AppConfig


class ArtiqClientConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "artiq_client"
    verbose_name = "ARTIQ master RPC client"
