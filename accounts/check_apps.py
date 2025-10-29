from django.apps import apps

print("Registered apps:")
for app in apps.get_app_configs():
    print(f"- {app.label} (from {app.__module__})")