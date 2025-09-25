# apps/authentication/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_verification_email(self, user_id, email, verification_token, user_first_name):
    """Send verification email in background"""
    try:
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{verification_token}"
        
        subject = 'Verify your BusiMap account'
        
        # Try to render HTML template, fallback to simple text if template doesn't exist
        try:
            html_message = render_to_string('emails/email_verification.html', {
                'user_first_name': user_first_name,
                'verification_url': verification_url,
                'expires_hours': 24
            })
        except:
            html_message = None
        
        # Plain text message
        plain_message = f"""
Hello {user_first_name},

Welcome to BusiMap Rwanda!

Please verify your email address by clicking the link below:
{verification_url}

This link will expire in 24 hours.

If you didn't create an account, please ignore this email.

Best regards,
The BusiMap Rwanda Team
        """
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f"Background email verification sent to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {e}")
        
        # Retry the task with exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
            raise self.retry(countdown=countdown, exc=e)
        else:
            logger.error(f"Max retries exceeded for email to {email}")
            return False

@shared_task(bind=True, max_retries=3)
def send_password_reset_email(self, user_id, email, reset_token, user_first_name):
    """Send password reset email in background"""
    try:
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{reset_token}"
        
        subject = 'Reset your BusiMap password'
        
        # Try to render HTML template
        try:
            html_message = render_to_string('emails/password_reset.html', {
                'user_first_name': user_first_name,
                'reset_url': reset_url,
                'expires_hours': 24
            })
        except:
            html_message = None
        
        # Plain text message
        plain_message = f"""
Hello {user_first_name},

You requested a password reset for your BusiMap Rwanda account.

Click the link below to reset your password:
{reset_url}

This link will expire in 24 hours.

If you didn't request this reset, please ignore this email.

Best regards,
The BusiMap Rwanda Team
        """
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f"Password reset email sent to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {e}")
        
        if self.request.retries < self.max_retries:
            countdown = 60 * (2 ** self.request.retries)
            raise self.retry(countdown=countdown, exc=e)
        else:
            logger.error(f"Max retries exceeded for password reset email to {email}")
            return False