from django.apps import AppConfig


class AmsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ams'
    
    def ready(self):
        import ams.signals  # Ensure signals are imported and registered
        import ams.helper
