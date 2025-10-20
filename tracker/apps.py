from django.apps import AppConfig


class TrackerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tracker"

    def ready(self):  # noqa: D401
        # Import signal handlers
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
