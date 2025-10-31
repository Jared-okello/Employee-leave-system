from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from accounts.models import CustomUser
from datetime import date

class LeaveType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    max_days = models.PositiveIntegerField(default=30)
    can_carry_forward = models.BooleanField(default=False)
    requires_approval = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Leave Type"
        verbose_name_plural = "Leave Types"

class LeaveRequest(models.Model):
    PENDING = 'P'
    APPROVED = 'A'
    REJECTED = 'R'
    CANCELLED = 'C'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (CANCELLED, 'Cancelled'),
    ]
    
    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default=PENDING)
    approved_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_leaves'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    emergency_contact = models.CharField(max_length=100, blank=True, null=True)
    address_during_leave = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.get_status_display()})"
    
    def clean(self):
        """Validate the leave request data"""
        errors = {}
        
        # Validate that both dates are provided
        if not self.start_date:
            errors['start_date'] = 'Start date is required.'
        if not self.end_date:
            errors['end_date'] = 'End date is required.'
        
        # Only proceed with date validation if both dates are provided
        if self.start_date and self.end_date:
            # Validate that end_date is not before start_date
            if self.end_date < self.start_date:
                errors['end_date'] = 'End date cannot be before start date.'
            
            # Validate that dates are not in the past (for new requests)
            if self.pk is None:  # Only for new instances
                if self.start_date < date.today():
                    errors['start_date'] = 'Cannot apply for leave in the past.'
            
            # Validate duration is positive
            duration = (self.end_date - self.start_date).days + 1
            if duration <= 0:
                errors['end_date'] = 'Leave duration must be at least 1 day.'
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Run validation before saving"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def duration(self):
        """Calculate total number of leave days"""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0  # Return 0 if dates are not set
    
    @property
    def is_approved(self):
        return self.status == self.APPROVED
    
    @property
    def is_pending(self):
        return self.status == self.PENDING
    
    @property
    def is_active(self):
        """Check if the leave is currently active (today is between start and end dates)"""
        if self.start_date and self.end_date:
            today = date.today()
            return self.start_date <= today <= self.end_date
        return False
    
    def can_be_cancelled(self):
        """Check if leave request can be cancelled"""
        if not self.start_date:
            return False
        return self.status in [self.PENDING, self.APPROVED] and self.start_date > date.today()
    
    def get_working_days(self):
        """Calculate working days excluding weekends"""
        if not self.start_date or not self.end_date:
            return 0
            
        from datetime import timedelta
        
        current_date = self.start_date
        working_days = 0
        
        while current_date <= self.end_date:
            # Skip weekends (Saturday=5, Sunday=6)
            if current_date.weekday() < 5:
                working_days += 1
            current_date += timedelta(days=1)
        
        return working_days
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Leave Request"
        verbose_name_plural = "Leave Requests"

class LeaveBalance(models.Model):
    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    remaining_days = models.PositiveIntegerField(default=0)
    carried_forward_days = models.PositiveIntegerField(default=0)
    total_earned_days = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('employee', 'leave_type')
        verbose_name = "Leave Balance"
        verbose_name_plural = "Leave Balances"
    
    def __str__(self):
        return f"{self.employee}: {self.leave_type} ({self.remaining_days} days)"
    
    def update_balance(self, days_used):
        """Update balance when leave is taken"""
        if days_used <= self.remaining_days:
            self.remaining_days -= days_used
            self.save()
            return True
        return False
    
    def reset_balance(self):
        """Reset balance to maximum days for the leave type"""
        self.remaining_days = self.leave_type.max_days
        self.carried_forward_days = 0
        self.total_earned_days = self.leave_type.max_days
        self.save()
    
    @property
    def is_low_balance(self):
        """Check if balance is low (less than 5 days)"""
        return self.remaining_days <= 5
    
    @property
    def utilization_percentage(self):
        """Calculate utilization percentage"""
        if self.total_earned_days > 0:
            return ((self.total_earned_days - self.remaining_days) / self.total_earned_days) * 100
        return 0

class LeaveAccrual(models.Model):
    """Track how leave days are accrued over time"""
    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='leave_accruals')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    accrual_date = models.DateField()
    days_accrued = models.PositiveIntegerField()
    description = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f"{self.employee} - {self.days_accrued} days on {self.accrual_date}"
    
    class Meta:
        ordering = ['-accrual_date']
        verbose_name = "Leave Accrual"
        verbose_name_plural = "Leave Accruals"

class Holiday(models.Model):
    """Store company holidays to exclude from leave calculations"""
    name = models.CharField(max_length=100)
    date = models.DateField()
    recurring = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} ({self.date})"
    
    def is_holiday(self, check_date):
        """Check if a specific date is a holiday"""
        if self.recurring:
            return check_date.month == self.date.month and check_date.day == self.date.day
        return check_date == self.date
    
    class Meta:
        ordering = ['date']
        verbose_name = "Holiday"
        verbose_name_plural = "Holidays"