from django.contrib import admin
from django.urls import path, include
from accounts.views import SignUpView
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication URLs
    path('accounts/', include('accounts.urls')),
    
    # Include other app URLs
    path('', include('leaves.urls')),  # Assuming leaves app has its URLs
    path('api/', include('api.urls')),  # Assuming api app has its URLs
]
# Add redirect for root URL
from django.shortcuts import redirect
urlpatterns += [
    path('', lambda request: redirect('leave-list')),
]