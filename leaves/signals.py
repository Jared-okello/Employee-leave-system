from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import LeaveRequest, LeaveBalance

@receiver(post_save, sender=LeaveRequest)
def update_leave_balance(sender, instance, created, **kwargs):
    """Update leave balance when a leave request is approved"""
    if instance.status == LeaveRequest.APPROVED:
        try:
            balance = LeaveBalance.objects.get(
                employee=instance.employee,
                leave_type=instance.leave_type
            )
            balance.update_balance(instance.duration)
        except LeaveBalance.DoesNotExist:
            pass