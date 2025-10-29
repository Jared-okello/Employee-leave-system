from django.contrib import admin
from django.urls import path, include
from accounts.views import SignUpView
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication URLs
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Include other app URLs
    path('', include('leaves.urls')),  # Assuming leaves app has its URLs
    path('api/', include('api.urls')),  # Assuming api app has its URLs
]