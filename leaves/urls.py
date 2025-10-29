from django.urls import path
from .views import LeaveRequestListView, LeaveRequestCreateView, LeaveRequestUpdateView

urlpatterns = [
    path('', LeaveRequestListView.as_view(), name='leave-list'),
    path('new/', LeaveRequestCreateView.as_view(), name='leave-create'),
    path('<int:pk>/approve/', LeaveRequestUpdateView.as_view(), name='leave-approve'),
]