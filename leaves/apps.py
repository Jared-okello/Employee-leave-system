from django.apps import AppConfig

class LeaveConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'leaves'
    verbose_name = 'Leave Management'
    
    def ready(self):
        """
        Import signals when the app is ready.
        This ensures that signal handlers are connected.
        """
        import leaves.signals