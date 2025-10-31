from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from accounts.models import CustomUser
from .models import LeaveRequest, LeaveType

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15)
    department = forms.CharField(max_length=100)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'phone', 'department', 'password1', 'password2')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

class LeaveRequestForm(forms.ModelForm):
    # Add emergency contact and address fields from enhanced model
    emergency_contact = forms.CharField(
        max_length=100,
        required=False,
        help_text="Emergency contact person and phone number"
    )
    address_during_leave = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text="Your address during leave period (optional)"
    )
    
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason', 'emergency_contact', 'address_during_leave']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Please provide a detailed reason for your leave...'}),
            'leave_type': forms.Select(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'start_date': 'First day of leave',
            'end_date': 'Last day of leave (inclusive)',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  # Get user from view
        super().__init__(*args, **kwargs)
        
        # Only show active leave types
        self.fields['leave_type'].queryset = LeaveType.objects.all()
        
        # Add CSS classes to all fields
        for field_name, field in self.fields.items():
            if field_name not in ['reason', 'address_during_leave']:
                field.widget.attrs.update({'class': 'form-control'})
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        leave_type = cleaned_data.get('leave_type')
        
        if start_date and end_date:
            # Check if end date is before start date
            if end_date < start_date:
                raise ValidationError({
                    'end_date': 'End date cannot be before start date.'
                })
            
            # Check if dates are in the past
            today = timezone.now().date()
            if start_date < today:
                raise ValidationError({
                    'start_date': 'Cannot apply for leave in the past.'
                })
            
            # Calculate duration
            duration = (end_date - start_date).days + 1
            
            # Check if duration is positive
            if duration <= 0:
                raise ValidationError('Leave duration must be at least 1 day.')
            
            # Check leave balance if user is provided
            if self.user and leave_type:
                try:
                    from .models import LeaveBalance
                    balance = LeaveBalance.objects.get(
                        employee=self.user,
                        leave_type=leave_type
                    )
                    if balance.remaining_days < duration:
                        raise ValidationError(
                            f'Insufficient leave balance. You have {balance.remaining_days} days remaining but requested {duration} days.'
                        )
                except LeaveBalance.DoesNotExist:
                    raise ValidationError('No leave balance found for this leave type.')
            
            # Store duration in cleaned_data for use in view if needed
            cleaned_data['duration'] = duration
        
        return cleaned_data

class LeaveApprovalForm(forms.ModelForm):
    """Form for managers to approve/reject leave requests"""
    manager_notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text="Optional notes for the employee"
    )
    
    class Meta:
        model = LeaveRequest
        fields = ['status']
        widgets = {
            'status': forms.RadioSelect()
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the default status choices and use our custom ones
        self.fields['status'].choices = [
            (LeaveRequest.APPROVED, '✅ Approve'),
            (LeaveRequest.REJECTED, '❌ Reject'),
        ]

class LeaveBalanceForm(forms.ModelForm):
    """Form for HR to manage leave balances"""
    class Meta:
        from .models import LeaveBalance
        model = LeaveBalance
        fields = ['employee', 'leave_type', 'remaining_days', 'carried_forward_days', 'total_earned_days']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'leave_type': forms.Select(attrs={'class': 'form-control'}),
            'remaining_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'carried_forward_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'total_earned_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

class LeaveTypeForm(forms.ModelForm):
    """Form for managing leave types"""
    class Meta:
        model = LeaveType
        fields = ['name', 'max_days', 'can_carry_forward', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'max_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
        help_texts = {
            'can_carry_forward': 'Allow unused days to be carried to next year',
        }

# FIXED: Form for filtering leave requests - no database access during import
class LeaveFilterForm(forms.Form):
    """Form for filtering leave requests in list views"""
    STATUS_CHOICES = [('', 'All Statuses')] + list(LeaveRequest.STATUS_CHOICES)
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    leave_type = forms.ChoiceField(
        choices=[],  # Will be populated in __init__
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate leave_type choices here to avoid database access during import
        leave_type_choices = [('', 'All Types')] + [
            (lt.id, lt.name) for lt in LeaveType.objects.all()
        ]
        self.fields['leave_type'].choices = leave_type_choices