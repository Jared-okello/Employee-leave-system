from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from .models import LeaveType, LeaveRequest, LeaveBalance

User = get_user_model()

class LeaveTypeModelTest(TestCase):
    def setUp(self):
        self.leave_type = LeaveType.objects.create(
            name='Annual Leave',
            max_days=21,
            can_carry_forward=True,
            requires_approval=True
        )
    
    def test_leave_type_creation(self):
        """Test that leave type is created successfully"""
        self.assertEqual(self.leave_type.name, 'Annual Leave')
        self.assertEqual(self.leave_type.max_days, 21)
        self.assertTrue(self.leave_type.can_carry_forward)
        self.assertTrue(self.leave_type.requires_approval)
    
    def test_leave_type_string_representation(self):
        """Test the string representation of leave type"""
        self.assertEqual(str(self.leave_type), 'Annual Leave')
    
    def test_leave_type_unique_name(self):
        """Test that leave type names must be unique"""
        with self.assertRaises(Exception):
            LeaveType.objects.create(name='Annual Leave', max_days=15)

class LeaveRequestModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.manager = User.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='managerpass123',
            is_staff=True
        )
        self.leave_type = LeaveType.objects.create(name='Sick Leave', max_days=10)
        
        # Create leave balance for user
        LeaveBalance.objects.create(
            employee=self.user,
            leave_type=self.leave_type,
            remaining_days=10
        )
        
        self.leave_request = LeaveRequest.objects.create(
            employee=self.user,
            leave_type=self.leave_type,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=3),
            reason='Medical appointment',
            status=LeaveRequest.PENDING
        )
    
    def test_leave_request_creation(self):
        """Test that leave request is created successfully"""
        self.assertEqual(self.leave_request.employee, self.user)
        self.assertEqual(self.leave_request.leave_type, self.leave_type)
        self.assertEqual(self.leave_request.status, LeaveRequest.PENDING)
        self.assertEqual(self.leave_request.reason, 'Medical appointment')
    
    def test_leave_request_duration_calculation(self):
        """Test duration property calculation"""
        expected_duration = 3  # 1, 2, 3 = 3 days
        self.assertEqual(self.leave_request.duration, expected_duration)
    
    def test_leave_request_string_representation(self):
        """Test the string representation of leave request"""
        expected_str = f"{self.user} - {self.leave_type} (Pending)"
        self.assertEqual(str(self.leave_request), expected_str)
    
    def test_leave_request_status_properties(self):
        """Test status helper properties"""
        self.assertTrue(self.leave_request.is_pending)
        self.assertFalse(self.leave_request.is_approved)
        
        # Test approved status
        self.leave_request.status = LeaveRequest.APPROVED
        self.assertTrue(self.leave_request.is_approved)
        self.assertFalse(self.leave_request.is_pending)
    
    def test_leave_request_validation(self):
        """Test leave request validation"""
        # Test end date before start date
        invalid_request = LeaveRequest(
            employee=self.user,
            leave_type=self.leave_type,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=2),
            reason='Invalid dates'
        )
        
        with self.assertRaises(Exception):
            invalid_request.full_clean()
    
    def test_leave_request_can_be_cancelled(self):
        """Test can_be_cancelled method"""
        # Future leave can be cancelled
        self.assertTrue(self.leave_request.can_be_cancelled())
        
        # Past leave cannot be cancelled
        past_request = LeaveRequest.objects.create(
            employee=self.user,
            leave_type=self.leave_type,
            start_date=date.today() - timedelta(days=5),
            end_date=date.today() - timedelta(days=3),
            reason='Past leave'
        )
        self.assertFalse(past_request.can_be_cancelled())

class LeaveBalanceModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.leave_type = LeaveType.objects.create(name='Annual Leave', max_days=21)
        self.balance = LeaveBalance.objects.create(
            employee=self.user,
            leave_type=self.leave_type,
            remaining_days=15,
            carried_forward_days=5,
            total_earned_days=20
        )
    
    def test_leave_balance_creation(self):
        """Test that leave balance is created successfully"""
        self.assertEqual(self.balance.employee, self.user)
        self.assertEqual(self.balance.leave_type, self.leave_type)
        self.assertEqual(self.balance.remaining_days, 15)
        self.assertEqual(self.balance.carried_forward_days, 5)
        self.assertEqual(self.balance.total_earned_days, 20)
    
    def test_leave_balance_string_representation(self):
        """Test the string representation of leave balance"""
        expected_str = f"{self.user}: {self.leave_type} (15 days)"
        self.assertEqual(str(self.balance), expected_str)
    
    def test_leave_balance_update_method(self):
        """Test update_balance method"""
        # Successful update
        result = self.balance.update_balance(5)
        self.assertTrue(result)
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.remaining_days, 10)
        
        # Failed update (insufficient balance)
        result = self.balance.update_balance(15)
        self.assertFalse(result)
        self.assertEqual(self.balance.remaining_days, 10)  # Unchanged
    
    def test_leave_balance_unique_together(self):
        """Test unique together constraint"""
        with self.assertRaises(Exception):
            LeaveBalance.objects.create(
                employee=self.user,
                leave_type=self.leave_type,
                remaining_days=10
            )

class LeaveViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.manager = User.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='managerpass123',
            is_staff=True
        )
        self.leave_type = LeaveType.objects.create(name='Annual Leave', max_days=21)
        
        # Create leave balance
        LeaveBalance.objects.create(
            employee=self.user,
            leave_type=self.leave_type,
            remaining_days=21
        )
        
        # Create leave request
        self.leave_request = LeaveRequest.objects.create(
            employee=self.user,
            leave_type=self.leave_type,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=5),
            reason='Vacation',
            status=LeaveRequest.PENDING
        )
    
    def test_leave_list_view_authenticated(self):
        """Test leave list view for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('leave-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'leaves/leave_list.html')
        self.assertContains(response, 'Vacation')
    
    def test_leave_list_view_unauthenticated(self):
        """Test leave list view redirects for unauthenticated user"""
        response = self.client.get(reverse('leave-list'))
        self.assertRedirects(response, f'/accounts/login/?next={reverse("leave-list")}')
    
    def test_leave_create_view_get(self):
        """Test leave create view GET request"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('leave-create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'leaves/leave_form.html')
        self.assertContains(response, 'Leave Request Form')
    
    def test_leave_create_view_post_valid(self):
        """Test leave create view with valid POST data"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'leave_type': self.leave_type.id,
            'start_date': date.today() + timedelta(days=10),
            'end_date': date.today() + timedelta(days=12),
            'reason': 'Family event',
            'emergency_contact': 'John Doe - 1234567890',
            'address_during_leave': 'Home address'
        }
        
        response = self.client.post(reverse('leave-create'), data)
        
        # Should redirect to leave list on success
        self.assertRedirects(response, reverse('leave-list'))
        
        # Check that leave request was created
        self.assertTrue(LeaveRequest.objects.filter(reason='Family event').exists())
    
    def test_leave_create_view_post_insufficient_balance(self):
        """Test leave create view with insufficient balance"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'leave_type': self.leave_type.id,
            'start_date': date.today() + timedelta(days=10),
            'end_date': date.today() + timedelta(days=35),  # 26 days - more than balance
            'reason': 'Long vacation'
        }
        
        response = self.client.post(reverse('leave-create'), data)
        
        # Should stay on form page with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Insufficient leave balance')
    
    def test_leave_detail_view(self):
        """Test leave detail view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('leave-detail', args=[self.leave_request.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'leaves/leave_detail.html')
        self.assertContains(response, 'Vacation')
    
    def test_leave_update_view(self):
        """Test leave update view for pending leave"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'leave_type': self.leave_type.id,
            'start_date': date.today() + timedelta(days=1),
            'end_date': date.today() + timedelta(days=3),  # Shorter duration
            'reason': 'Updated reason'
        }
        
        response = self.client.post(
            reverse('leave-update', args=[self.leave_request.id]), 
            data
        )
        
        self.assertRedirects(response, reverse('leave-list'))
        
        # Check that leave request was updated
        self.leave_request.refresh_from_db()
        self.assertEqual(self.leave_request.reason, 'Updated reason')
    
    def test_leave_delete_view(self):
        """Test leave delete view"""
        self.client.login(username='testuser', password='testpass123')
        
        # Create a new leave request to delete
        new_leave = LeaveRequest.objects.create(
            employee=self.user,
            leave_type=self.leave_type,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=12),
            reason='To be deleted'
        )
        
        response = self.client.post(reverse('leave-delete', args=[new_leave.id]))
        
        self.assertRedirects(response, reverse('leave-list'))
        self.assertFalse(LeaveRequest.objects.filter(id=new_leave.id).exists())

class LeaveFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.leave_type = LeaveType.objects.create(name='Annual Leave', max_days=21)
        LeaveBalance.objects.create(
            employee=self.user,
            leave_type=self.leave_type,
            remaining_days=21
        )
    
    def test_leave_request_form_valid_data(self):
        """Test LeaveRequestForm with valid data"""
        from .forms import LeaveRequestForm
        
        form_data = {
            'leave_type': self.leave_type.id,
            'start_date': date.today() + timedelta(days=5),
            'end_date': date.today() + timedelta(days=7),
            'reason': 'Valid leave request',
            'emergency_contact': 'Test Contact',
            'address_during_leave': 'Test Address'
        }
        
        form = LeaveRequestForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
    
    def test_leave_request_form_invalid_dates(self):
        """Test LeaveRequestForm with invalid dates"""
        from .forms import LeaveRequestForm
        
        form_data = {
            'leave_type': self.leave_type.id,
            'start_date': date.today() + timedelta(days=5),
            'end_date': date.today() + timedelta(days=3),  # End before start
            'reason': 'Invalid dates'
        }
        
        form = LeaveRequestForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('end_date', form.errors)
    
    def test_leave_request_form_past_dates(self):
        """Test LeaveRequestForm with past dates"""
        from .forms import LeaveRequestForm
        
        form_data = {
            'leave_type': self.leave_type.id,
            'start_date': date.today() - timedelta(days=5),  # Past date
            'end_date': date.today() + timedelta(days=3),
            'reason': 'Past dates'
        }
        
        form = LeaveRequestForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('start_date', form.errors)

class LeaveIntegrationTest(TestCase):
    """Integration tests for complete leave workflow"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='employee',
            email='employee@example.com',
            password='testpass123'
        )
        self.manager = User.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='managerpass123',
            is_staff=True
        )
        self.leave_type = LeaveType.objects.create(
            name='Annual Leave',
            max_days=21,
            requires_approval=True
        )
        
        # Set up initial balance
        LeaveBalance.objects.create(
            employee=self.user,
            leave_type=self.leave_type,
            remaining_days=21
        )
    
    def test_complete_leave_workflow(self):
        """Test complete leave workflow from request to approval"""
        # 1. Employee logs in and applies for leave
        self.client.login(username='employee', password='testpass123')
        
        leave_data = {
            'leave_type': self.leave_type.id,
            'start_date': date.today() + timedelta(days=10),
            'end_date': date.today() + timedelta(days=12),
            'reason': 'Integration test leave',
            'emergency_contact': 'Test Contact',
            'address_during_leave': 'Test Address'
        }
        
        response = self.client.post(reverse('leave-create'), leave_data)
        self.assertRedirects(response, reverse('leave-list'))
        
        # Verify leave was created with pending status
        leave_request = LeaveRequest.objects.get(reason='Integration test leave')
        self.assertEqual(leave_request.status, LeaveRequest.PENDING)
        
        # 2. Manager logs in and approves the leave
        self.client.login(username='manager', password='managerpass123')
        
        # Simulate approval (you'd need to implement approval views)
        leave_request.status = LeaveRequest.APPROVED
        leave_request.approved_by = self.manager
        leave_request.save()
        
        # 3. Verify balance was updated
        balance = LeaveBalance.objects.get(employee=self.user, leave_type=self.leave_type)
        expected_remaining = 21 - leave_request.duration  # 21 - 3 = 18
        self.assertEqual(balance.remaining_days, expected_remaining)

# Run specific test:
# python manage.py test leaves.tests.LeaveTypeModelTest
# python manage.py test leaves.tests.LeaveViewsTest.test_leave_create_view_post_valid