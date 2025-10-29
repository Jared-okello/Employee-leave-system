from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .models import LeaveRequest
from .forms import LeaveRequestForm

class LeaveRequestListView(LoginRequiredMixin, ListView):
    model = LeaveRequest
    template_name = 'leaves/leave_list.html'
    
    def get_queryset(self):
        return LeaveRequest.objects.filter(employee=self.request.user)

class LeaveRequestCreateView(LoginRequiredMixin, CreateView):
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'leaves/leave_form.html'
    success_url = reverse_lazy('leave-list')
    
    def form_valid(self, form):
        form.instance.employee = self.request.user
        return super().form_valid(form)

class LeaveRequestUpdateView(LoginRequiredMixin, UpdateView):
    model = LeaveRequest
    fields = ['status']
    template_name = 'leaves/leave_approval.html'
    
    def get_queryset(self):
        return LeaveRequest.objects.filter(employee__manager=self.request.user)
