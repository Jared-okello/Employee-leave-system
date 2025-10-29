from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    EMPLOYEE = 'EMP'
    MANAGER = 'MGR'
    HR = 'HR'
    ADMIN = 'ADM'
    
    ROLE_CHOICES = [
        (EMPLOYEE, 'Employee'),
        (MANAGER, 'Manager'),
        (HR, 'HR Personnel'),
        (ADMIN, 'System Admin'),
    ]
    
    role = models.CharField(max_length=3, choices=ROLE_CHOICES, default=EMPLOYEE)
    phone = models.CharField(max_length=15, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"
