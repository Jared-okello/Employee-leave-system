from django.db import models
from accounts.models import CustomUser

class LeaveType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    max_days = models.PositiveIntegerField(default=30)
    can_carry_forward = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name

class LeaveRequest(models.Model):
    PENDING = 'P'
    APPROVED = 'A'
    REJECTED = 'R'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]
    
    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default=PENDING)
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.status})"
    
    @property
    def duration(self):
        return (self.end_date - self.start_date).days + 1

class LeaveBalance(models.Model):
    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    remaining_days = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ('employee', 'leave_type')
    
    def __str__(self):
        return f"{self.employee}: {self.leave_type} ({self.remaining_days} days)"