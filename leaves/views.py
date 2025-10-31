from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.db.models import Q
from django.utils import timezone
from .models import LeaveRequest, LeaveType, LeaveBalance
from .forms import LeaveRequestForm

class StaffRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure user is staff member"""
    def test_func(self):
        return self.request.user.is_staff

class ManagerRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure user is a manager"""
    def test_func(self):
        return hasattr(self.request.user, 'is_manager') and self.request.user.is_manager

class LeaveRequestListView(LoginRequiredMixin, ListView):
    model = LeaveRequest
    template_name = 'leaves/leave_list.html'
    context_object_name = 'leaves'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = LeaveRequest.objects.filter(employee=self.request.user)
        
        # Filter by status if provided
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by leave type if provided
        leave_type_filter = self.request.GET.get('leave_type')
        if leave_type_filter:
            queryset = queryset.filter(leave_type_id=leave_type_filter)
            
        return queryset.select_related('leave_type', 'approved_by').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['leave_types'] = LeaveType.objects.all()
        context['status_choices'] = LeaveRequest.STATUS_CHOICES
        context['current_status'] = self.request.GET.get('status', '')
        context['current_leave_type'] = self.request.GET.get('leave_type', '')
        
        # Add leave balances to context
        context['leave_balances'] = LeaveBalance.objects.filter(
            employee=self.request.user
        ).select_related('leave_type')
        
        return context

class LeaveRequestDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = LeaveRequest
    template_name = 'leaves/leave_detail.html'
    context_object_name = 'leave'
    
    def test_func(self):
        leave = self.get_object()
        return self.request.user == leave.employee or self.request.user.is_staff

class LeaveRequestCreateView(LoginRequiredMixin, CreateView):
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'leaves/leave_form.html'
    success_url = reverse_lazy('leave-list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.employee = self.request.user
        
        # Check leave balance before saving
        leave_type = form.cleaned_data['leave_type']
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        duration = (end_date - start_date).days + 1
        
        try:
            balance = LeaveBalance.objects.get(
                employee=self.request.user,
                leave_type=leave_type
            )
            if balance.remaining_days < duration:
                messages.error(
                    self.request,
                    f'Insufficient leave balance. You have {balance.remaining_days} days remaining but requested {duration} days.'
                )
                return self.form_invalid(form)
                
        except LeaveBalance.DoesNotExist:
            messages.error(
                self.request,
                'No leave balance found for this leave type.'
            )
            return self.form_invalid(form)
        
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Leave request submitted successfully for {duration} days. Status: Pending'
        )
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['leave_balances'] = LeaveBalance.objects.filter(
            employee=self.request.user
        ).select_related('leave_type')
        return context

class LeaveRequestUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'leaves/leave_form.html'
    
    def test_func(self):
        leave = self.get_object()
        return self.request.user == leave.employee and leave.status == LeaveRequest.PENDING
    
    def get_success_url(self):
        return reverse_lazy('leave-list')
    
    def form_valid(self, form):
        # Only allow editing if status is pending
        if form.instance.status != LeaveRequest.PENDING:
            messages.error(self.request, 'Cannot edit leave request that is not pending.')
            return self.form_invalid(form)
        
        response = super().form_valid(form)
        messages.success(self.request, 'Leave request updated successfully.')
        return response

class LeaveRequestDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = LeaveRequest
    template_name = 'leaves/leave_confirm_delete.html'
    success_url = reverse_lazy('leave-list')
    
    def test_func(self):
        leave = self.get_object()
        return self.request.user == leave.employee and leave.status == LeaveRequest.PENDING
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Leave request cancelled successfully.')
        return super().delete(request, *args, **kwargs)

class LeaveApprovalListView(LoginRequiredMixin, ManagerRequiredMixin, ListView):
    model = LeaveRequest
    template_name = 'leaves/leave_approval_list.html'
    context_object_name = 'pending_leaves'
    paginate_by = 10
    
    def get_queryset(self):
        # Get leaves for employees where current user is manager
        return LeaveRequest.objects.filter(
            status=LeaveRequest.PENDING,
            employee__manager=self.request.user
        ).select_related('employee', 'leave_type').order_by('start_date')

class LeaveApprovalUpdateView(LoginRequiredMixin, ManagerRequiredMixin, UpdateView):
    model = LeaveRequest
    fields = ['status']
    template_name = 'leaves/leave_approval.html'
    
    def get_queryset(self):
        return LeaveRequest.objects.filter(
            status=LeaveRequest.PENDING,
            employee__manager=self.request.user
        )
    
    def form_valid(self, form):
        form.instance.approved_by = self.request.user
        
        response = super().form_valid(form)
        
        status_display = form.instance.get_status_display()
        messages.success(
            self.request,
            f'Leave request {status_display.lower()} successfully.'
        )
        return response
    
    def get_success_url(self):
        return reverse_lazy('leave-approval-list')

class LeaveBalanceListView(LoginRequiredMixin, ListView):
    model = LeaveBalance
    template_name = 'leaves/leave_balance_list.html'
    context_object_name = 'balances'
    
    def get_queryset(self):
        return LeaveBalance.objects.filter(
            employee=self.request.user
        ).select_related('leave_type')