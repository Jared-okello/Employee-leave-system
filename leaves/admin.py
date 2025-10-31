from django.contrib import admin
from django.utils.html import format_html
from .models import LeaveType, LeaveRequest, LeaveBalance

@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'max_days', 'can_carry_forward', 'requires_approval')
    list_filter = ('can_carry_forward', 'requires_approval')
    search_fields = ('name',)
    list_editable = ('max_days', 'can_carry_forward', 'requires_approval')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Leave Policy', {
            'fields': ('max_days', 'can_carry_forward', 'requires_approval')
        }),
    )

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = (
        'employee', 
        'leave_type', 
        'start_date', 
        'end_date', 
        'duration_display',
        'status_display',
        'created_at'
    )
    list_filter = ('status', 'leave_type', 'start_date', 'created_at')
    search_fields = ('employee__username', 'employee__email', 'reason')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'duration_display')
    list_per_page = 20
    
    # Add action for bulk approval/rejection
    actions = ['approve_leave_requests', 'reject_leave_requests']
    
    fieldsets = (
        ('Employee Information', {
            'fields': ('employee', 'leave_type')
        }),
        ('Leave Details', {
            'fields': (
                'start_date', 
                'end_date', 
                'duration_display',
                'reason',
                'emergency_contact',
                'address_during_leave'
            )
        }),
        ('Approval Information', {
            'fields': ('status', 'approved_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def duration_display(self, obj):
        return f"{obj.duration} day(s)"
    duration_display.short_description = 'Duration'
    
    def status_display(self, obj):
        status_colors = {
            'P': 'orange',    # Pending - orange
            'A': 'green',     # Approved - green
            'R': 'red',       # Rejected - red
            'C': 'gray',      # Cancelled - gray
        }
        color = status_colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def approve_leave_requests(self, request, queryset):
        updated = queryset.filter(status='P').update(status='A', approved_by=request.user)
        self.message_user(request, f'{updated} leave request(s) approved successfully.')
    approve_leave_requests.short_description = "Approve selected pending leave requests"
    
    def reject_leave_requests(self, request, queryset):
        updated = queryset.filter(status='P').update(status='R', approved_by=request.user)
        self.message_user(request, f'{updated} leave request(s) rejected.')
    reject_leave_requests.short_description = "Reject selected pending leave requests"
    
    def get_queryset(self, request):
        # Optimize database queries
        return super().get_queryset(request).select_related('employee', 'leave_type', 'approved_by')
    
    def save_model(self, request, obj, form, change):
        # Auto-set approved_by when status changes to approved
        if obj.status == 'A' and not obj.approved_by:
            obj.approved_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = (
        'employee', 
        'leave_type', 
        'remaining_days_display',
        'carried_forward_days',
        'total_earned_days',
        'last_updated'
    )
    list_filter = ('leave_type', 'last_updated')
    search_fields = ('employee__username', 'employee__email')
    readonly_fields = ('last_updated',)
    list_per_page = 25
    
    # Add action to reset balances
    actions = ['reset_balances']
    
    fieldsets = (
        ('Employee Information', {
            'fields': ('employee', 'leave_type')
        }),
        ('Balance Details', {
            'fields': (
                'remaining_days',
                'carried_forward_days', 
                'total_earned_days'
            )
        }),
        ('Metadata', {
            'fields': ('last_updated',),
            'classes': ('collapse',)
        }),
    )
    
    def remaining_days_display(self, obj):
        """Color code remaining days based on threshold"""
        if obj.remaining_days <= 5:
            color = 'red'
        elif obj.remaining_days <= 10:
            color = 'orange'
        else:
            color = 'green'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} days</span>',
            color,
            obj.remaining_days
        )
    remaining_days_display.short_description = 'Remaining Days'
    
    def reset_balances(self, request, queryset):
        """Action to reset balances to maximum for selected records"""
        for balance in queryset:
            balance.remaining_days = balance.leave_type.max_days
            balance.save()
        self.message_user(request, f'{queryset.count()} leave balances reset to maximum days.')
    reset_balances.short_description = "Reset selected balances to maximum days"
    
    def get_queryset(self, request):
        # Optimize database queries
        return super().get_queryset(request).select_related('employee', 'leave_type')