from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('login/', views.custom_login, name='login'),
     path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
   path('resend-verification/', views.resend_verification_email, name='resend_verification'),
    path('profile/', views.profile, name='profile'),
]