# api/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Add a simple test pattern
    path('', views.LeaveListAPIView.as_view(), name='api-root'),
    # path('leaves/', views.LeaveListAPIView.as_view(), name='api-leave-list'),
]