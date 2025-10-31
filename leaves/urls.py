# leaves/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.LeaveRequestListView.as_view(), name='leave-list'),
    path('create/', views.LeaveRequestCreateView.as_view(), name='leave-create'),
    path('<int:pk>/', views.LeaveRequestDetailView.as_view(), name='leave-detail'),
    path('<int:pk>/update/', views.LeaveRequestUpdateView.as_view(), name='leave-update'),
    path('<int:pk>/delete/', views.LeaveRequestDeleteView.as_view(), name='leave-delete'),
    path('approval/', views.LeaveApprovalListView.as_view(), name='leave-approval-list'),
    path('approval/<int:pk>/', views.LeaveApprovalUpdateView.as_view(), name='leave-approval'),
    path('balances/', views.LeaveBalanceListView.as_view(), name='leave-balances'),
]