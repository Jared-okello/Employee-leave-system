from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.sites.shortcuts import get_current_site
import logging
import smtplib

from .forms import CustomUserCreationForm, LoginForm
from .models import CustomUser

# Set up logger
logger = logging.getLogger(__name__)

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        try:
            user = form.save(commit=False)
            user.email_verified = False
            user.save()
            
            # Generate and send verification email
            token = user.generate_verification_token()
            email_sent = self.send_verification_email(user, token)
            
            if email_sent:
                messages.success(
                    self.request, 
                    'Registration successful! Please check your email to verify your account.'
                )
            else:
                # Store user info in session for resending email
                self.request.session['pending_verification_user_id'] = user.id
                self.request.session['pending_verification_email'] = user.email
                
                messages.warning(
                    self.request,
                    f'Account created successfully! However, we could not send the verification email to {user.email}. '
                    f'<a href="{reverse("resend_verification")}" class="alert-link">Click here to resend the verification email</a>.',
                    extra_tags='safe'
                )
            
            return redirect(self.success_url)
            
        except Exception as e:
            logger.error(f"Error during user registration: {str(e)}")
            messages.error(
                self.request,
                'An error occurred during registration. Please try again.'
            )
            return self.form_invalid(form)

    def send_verification_email(self, user, token):
        """
        Send verification email with comprehensive error handling
        """
        try:
            current_site = get_current_site(self.request)
            subject = f'Verify your email address for {current_site.name}'
            
            # Create verification URL
            verification_url = self.request.build_absolute_uri(
                reverse('verify_email', kwargs={'token': token})
            )
            
            # Plain text message
            plain_message = f"""
Hi {user.username},

Welcome to {current_site.name}!

Please verify your email address by clicking the link below:

{verification_url}

This link will expire in 24 hours.

If you didn't create an account with us, please ignore this email.

Thank you!
The {current_site.name} Team
            """
            
            # HTML message
            html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .button {{ background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; }}
        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Verify Your Email</h1>
        </div>
        <div class="content">
            <p>Hi <strong>{user.username}</strong>,</p>
            <p>Welcome to <strong>{Employee_Leave_System}</strong>!</p>
            <p>Please verify your email address by clicking the button below:</p>
            <p style="text-align: center;">
                <a href="{verification_url}" class="button">Verify Email Address</a>
            </p>
            <p>Or copy and paste this link in your browser:</p>
            <p style="word-break: break-all;"><code>{verification_url}</code></p>
            <p><em>This link will expire in 24 hours.</em></p>
            <p>If you didn't create an account with us, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>Thank you!<br>The {current_site.name} Team</p>
        </div>
    </div>
</body>
</html>
            """
            
            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Verification email sent successfully to {user.email}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP Authentication failed. Check email credentials.")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error occurred: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
            return False


def verify_email(request, token):
    """
    Handle email verification with proper error handling
    """
    try:
        if not token:
            messages.error(request, 'Invalid verification link.')
            return redirect('login')
            
        user = CustomUser.objects.get(verification_token=token)
        user.email_verified = True
        user.verification_token = None  # Clear the token after verification
        user.save()
        
        # Clear any pending verification session data
        if 'pending_verification_user_id' in request.session:
            del request.session['pending_verification_user_id']
        if 'pending_verification_email' in request.session:
            del request.session['pending_verification_email']
        
        messages.success(request, 'Email verified successfully! You can now login.')
        logger.info(f"Email verified successfully for user: {user.username}")
        
    except CustomUser.DoesNotExist:
        messages.error(request, 'Invalid verification link. The link may have expired or already been used.')
        logger.warning(f"Invalid verification token attempted: {token}")
        
    except Exception as e:
        messages.error(request, 'An error occurred during email verification. Please try again.')
        logger.error(f"Error during email verification: {str(e)}")
    
    return redirect('login')


def custom_login(request):
    """
    Custom login view with email verification check and resend option
    """
    if request.user.is_authenticated:
        return redirect('leave-list')
        
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.email_verified:
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.username}!')
                    
                    # Redirect to next page if specified, otherwise to leave list
                    next_page = request.GET.get('next')
                    return redirect(next_page) if next_page else redirect('leave-list')
                else:
                    # Store user info for resending verification
                    request.session['pending_verification_user_id'] = user.id
                    request.session['pending_verification_email'] = user.email
                    
                    messages.error(
                        request, 
                        f'Please verify your email address ({user.email}) before logging in. '
                        f'<a href="{reverse("resend_verification")}" class="alert-link">Click here to resend the verification email</a>.',
                        extra_tags='safe'
                    )
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def resend_verification_email(request):
    """
    View to resend verification email with improved functionality
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        user_id = request.session.get('pending_verification_user_id')
        
        try:
            # Try to get user by session ID first, then by email
            if user_id:
                user = CustomUser.objects.get(id=user_id, email=email)
            else:
                user = CustomUser.objects.get(email=email)
                
            if user.email_verified:
                messages.info(request, 'Your email is already verified. You can login now.')
                # Clear session data
                if 'pending_verification_user_id' in request.session:
                    del request.session['pending_verification_user_id']
                if 'pending_verification_email' in request.session:
                    del request.session['pending_verification_email']
                return redirect('login')
            else:
                # Generate new token and send email
                token = user.generate_verification_token()
                signup_view = SignUpView()
                email_sent = signup_view.send_verification_email(user, token)
                
                if email_sent:
                    messages.success(request, 'Verification email sent! Please check your inbox and spam folder.')
                    logger.info(f"Verification email resent to {user.email}")
                else:
                    messages.error(
                        request, 
                        'Failed to send verification email. Please check your email address or try again later.'
                    )
                
                return redirect('login')
                
        except CustomUser.DoesNotExist:
            messages.error(request, 'No account found with this email address. Please sign up first.')
    
    # Pre-fill email from session if available
    initial_email = request.session.get('pending_verification_email', '')
    
    return render(request, 'accounts/resend_verification.html', {'initial_email': initial_email})


@login_required
def profile(request):
    """
    User profile page
    """
    return render(request, 'accounts/profile.html', {'user': request.user})