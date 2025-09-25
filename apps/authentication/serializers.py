# apps/authentication/serializers.py - COMPLETE AND WORKING VERSION
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    User, UserProfile, PhoneVerification, 
    EmailVerification, PasswordReset, UserLoginLog
)
import re
import json


class BaseSerializer(serializers.Serializer):
    """Base serializer for consistent error handling"""
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {'success': True, 'data': data}


class UserRegistrationSerializer(serializers.ModelSerializer):
    """User registration serializer with validation"""
    
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone_number',
            'password', 'confirm_password', 'preferred_language',
            'location_province', 'location_district', 'user_type'
        ]

    def validate_email(self, value):
        """Validate email is unique and format"""
        value = value.lower().strip()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_phone_number(self, value):
        """Validate Rwanda phone number format if provided"""
        if not value or not value.strip():
            return None
            
        # Normalize phone number
        value = value.strip()
        value = re.sub(r'[\s\-]', '', value)
        
        # Enhanced Rwanda phone patterns
        rwanda_phone_patterns = [
            r'^\+250[7][0-9]{8}$',  # +2507XXXXXXXX
            r'^250[7][0-9]{8}$',    # 2507XXXXXXXX
            r'^0[7][0-9]{8}$',      # 07XXXXXXXX
        ]
        
        # Check if any pattern matches
        if not any(re.match(pattern, value) for pattern in rwanda_phone_patterns):
            raise serializers.ValidationError(
                "Phone number must be in Rwanda format: +2507XXXXXXXX, 2507XXXXXXXX, or 07XXXXXXXX"
            )
        
        # Convert to consistent format for uniqueness check
        normalized_phone = value
        if value.startswith('07'):
            normalized_phone = '+250' + value[1:]
        elif value.startswith('250'):
            normalized_phone = '+' + value
            
        # Only check for uniqueness if the phone number is not empty
        if User.objects.filter(phone_number=normalized_phone).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        
        return normalized_phone

    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords don't match"})
        
        # Ensure phone_number is properly handled before validation
        phone_number = attrs.get('phone_number')
        if phone_number == '' or phone_number is None:
            attrs['phone_number'] = None
        
        attrs.pop('confirm_password')
        return attrs

    def create(self, validated_data):
        """Create user with encrypted password"""
        password = validated_data.pop('password')
        
        # Ensure phone_number is properly handled
        phone_number = validated_data.get('phone_number')
        if phone_number == '' or phone_number is None:
            validated_data['phone_number'] = None
        
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """User login serializer with enhanced validation - FIXED VERSION"""
    
    email = serializers.EmailField(required=True)  
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Validate login credentials - FIXED VERSION"""
        email = attrs.get('email', '').lower().strip()
        password = attrs.get('password')
        
        if not email:
            raise serializers.ValidationError("Email is required")

        # Get request context for IP and user agent
        request = self.context.get('request')
        ip_address = self.context.get('ip_address', '')
        user_agent = self.context.get('user_agent', '')

        # FIXED: Simplified lookup - use email directly
        try:
            user_obj = User.objects.get(email__iexact=email)
                
            if not user_obj.is_active:
                raise serializers.ValidationError("User account is disabled")
                
            if user_obj.is_locked:
                remaining_time = user_obj.locked_until - timezone.now()
                minutes = int(remaining_time.total_seconds() / 60)
                raise serializers.ValidationError(
                    f"Account is temporarily locked. Please try again in {minutes} minutes."
                )
                
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password")

        # FIXED: Use email for authentication instead of username
        user = authenticate(request=request, username=email, password=password)

        if not user:
            # Record failed attempt
            user_obj.record_login_attempt(
                success=False, 
                ip_address=ip_address,
                user_agent=user_agent,
                failure_reason='invalid_credentials'
            )
            raise serializers.ValidationError("Invalid email or password")

        # Record successful login
        user.record_login_attempt(
            success=True,
            ip_address=ip_address,
            user_agent=user_agent
        )

        attrs['user'] = user
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """User profile serializer"""
    
    profile = serializers.SerializerMethodField()
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    has_phone_number = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'full_name', 'profile_picture', 'date_of_birth',
            'location_province', 'location_district', 'location_sector', 'location_cell',
            'current_latitude', 'current_longitude',
            'user_type', 'preferred_language', 'notifications_enabled',
            'location_sharing_enabled', 'email_verified', 'phone_verified',
            'is_verified', 'has_phone_number', 'date_joined', 'profile'
        ]
        read_only_fields = [
            'id', 'email', 'phone_number', 'date_joined', 
            'email_verified', 'phone_verified', 'is_verified', 'has_phone_number'
        ]

    def get_profile(self, obj):
        """Get extended profile information"""
        try:
            profile = obj.profile
            return {
                'bio': profile.bio,
                'favorite_business_categories': profile.favorite_business_categories,
                'dietary_preferences': profile.dietary_preferences,
                'transportation_preferences': profile.transportation_preferences,
                'profile_visibility': profile.profile_visibility,
                'total_searches': profile.total_searches,
                'total_business_visits': profile.total_business_visits,
                'email_notifications': profile.email_notifications,
                'sms_notifications': profile.sms_notifications,
                'push_notifications': profile.push_notifications,
            }
        except UserProfile.DoesNotExist:
            return None

    def get_has_phone_number(self, obj):
        """Check if user has a phone number"""
        return bool(obj.phone_number and obj.phone_number.strip())


class PhoneVerificationRequestSerializer(serializers.Serializer):
    """Request phone verification code"""
    
    phone_number = serializers.CharField(max_length=20)

    def validate_phone_number(self, value):
        """Validate Rwanda phone number format"""
        if not value:
            raise serializers.ValidationError("Phone number is required")
            
        # Normalize phone number
        value = value.strip()
        value = re.sub(r'[\s\-]', '', value)
        
        # Enhanced Rwanda phone patterns
        rwanda_phone_patterns = [
            r'^\+250[7][0-9]{8}$',  # +2507XXXXXXXX
            r'^250[7][0-9]{8}$',    # 2507XXXXXXXX
            r'^0[7][0-9]{8}$',      # 07XXXXXXXX
        ]
        
        if not any(re.match(pattern, value) for pattern in rwanda_phone_patterns):
            raise serializers.ValidationError(
                "Phone number must be in Rwanda format: +2507XXXXXXXX, 2507XXXXXXXX, or 07XXXXXXXX"
            )
        
        # Convert to consistent format
        if value.startswith('07'):
            value = '+250' + value[1:]
        elif value.startswith('250'):
            value = '+' + value
            
        return value


class PhoneVerificationSerializer(serializers.Serializer):
    """Phone verification serializer"""
    
    verification_code = serializers.CharField(max_length=10)
    phone_number = serializers.CharField(max_length=20, required=False)

    def validate_verification_code(self, value):
        """Validate verification code format"""
        value = value.strip()
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError("Verification code must be 6 digits")
        return value

    def validate(self, attrs):
        """Additional validation for verification"""
        user = self.context.get('user')
        code = attrs.get('verification_code')
        phone_number = attrs.get('phone_number')

        if not user:
            raise serializers.ValidationError("User context required")

        # Use provided phone number or user's phone number
        target_phone = phone_number or user.phone_number
        
        if not target_phone:
            raise serializers.ValidationError("Phone number is required for verification")

        try:
            verification = PhoneVerification.objects.get(
                user=user,
                phone_number=target_phone,
                verification_code=code,
                is_verified=False
            )

            if verification.is_expired:
                raise serializers.ValidationError("Verification code has expired")
                
            if verification.attempts_exceeded:
                raise serializers.ValidationError("Maximum verification attempts exceeded")

        except PhoneVerification.DoesNotExist:
            # Increment attempts if verification exists but code is wrong
            try:
                verification = PhoneVerification.objects.get(
                    user=user,
                    phone_number=target_phone,
                    is_verified=False
                )
                verification.increment_attempts()
            except PhoneVerification.DoesNotExist:
                pass
                
            raise serializers.ValidationError("Invalid verification code")

        attrs['verification'] = verification
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    """Email verification serializer"""
    
    token = serializers.CharField(max_length=100)

    def validate(self, attrs):
        """Validate email verification token"""
        token = attrs.get('token')

        try:
            verification = EmailVerification.objects.select_related('user').get(
                verification_token=token,
                is_verified=False,
                expires_at__gt=timezone.now()  # Check expiration
            )
        except EmailVerification.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired verification token")

        attrs['verification'] = verification
        return attrs


class PasswordResetSerializer(serializers.Serializer):
    """Password reset request serializer"""
    
    email = serializers.EmailField()

    def validate_email(self, value):
        """Check if email exists"""
        value = value.lower().strip()
        try:
            user = User.objects.get(email__iexact=value, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("No active user found with this email address")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(validators=[validate_password])
    confirm_password = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords don't match"})

        token = attrs.get('token')

        try:
            reset = PasswordReset.objects.select_related('user').get(
                reset_token=token, 
                is_used=False,
                expires_at__gt=timezone.now()  # Check expiration
            )
        except PasswordReset.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired reset token")

        attrs['reset'] = reset
        return attrs


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    
    profile = serializers.JSONField(required=False, write_only=True)

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'profile_picture', 'date_of_birth',
            'location_province', 'location_district', 'location_sector', 'location_cell',
            'current_latitude', 'current_longitude',
            'preferred_language', 'notifications_enabled', 'location_sharing_enabled',
            'profile'
        ]

    def validate_profile(self, value):
        """Ensure profile data is properly formatted"""
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Invalid JSON format for profile data")
        
        if value is not None and not isinstance(value, dict):
            raise serializers.ValidationError("Profile data must be a dictionary")
        
        return value

    def update(self, instance, validated_data):
        """Update user and profile data"""
        profile_data = validated_data.pop('profile', {})
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update profile fields
        if profile_data and hasattr(instance, 'profile'):
            profile = instance.profile
            for attr, value in profile_data.items():
                if hasattr(profile, attr):
                    setattr(profile, attr, value)
            profile.save()

        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """Change password serializer"""
    
    current_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    confirm_password = serializers.CharField()

    def validate_current_password(self, value):
        """Validate current password"""
        user = self.context['user']
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect")
        return value

    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords don't match"})
        return attrs


class UserLoginLogSerializer(serializers.ModelSerializer):
    """Serializer for user login logs"""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = UserLoginLog
        fields = [
            'user_email', 'user_full_name', 'ip_address', 'user_agent', 'success', 
            'failure_reason', 'created_at'
        ]
        read_only_fields = ['created_at']


class AddPhoneNumberSerializer(serializers.Serializer):
    """Serializer for adding phone number to existing user"""
    
    phone_number = serializers.CharField(max_length=20)

    def validate_phone_number(self, value):
        """Validate Rwanda phone number format"""
        if not value:
            raise serializers.ValidationError("Phone number is required")
            
        # Normalize phone number
        value = value.strip()
        value = re.sub(r'[\s\-]', '', value)
        
        # Enhanced Rwanda phone patterns
        rwanda_phone_patterns = [
            r'^\+250[7][0-9]{8}$',  # +2507XXXXXXXX
            r'^250[7][0-9]{8}$',    # 2507XXXXXXXX
            r'^0[7][0-9]{8}$',      # 07XXXXXXXX
        ]
        
        if not any(re.match(pattern, value) for pattern in rwanda_phone_patterns):
            raise serializers.ValidationError(
                "Phone number must be in Rwanda format: +2507XXXXXXXX, 2507XXXXXXXX, or 07XXXXXXXX"
            )
        
        # Convert to consistent format for uniqueness check
        normalized_phone = value
        if value.startswith('07'):
            normalized_phone = '+250' + value[1:]
        elif value.startswith('250'):
            normalized_phone = '+' + value
            
        if User.objects.filter(phone_number=normalized_phone).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        
        return normalized_phone


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user serializer for public profiles"""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'profile_picture', 'user_type',
            'location_province', 'location_district'
        ]
        read_only_fields = fields


class UserRegistrationResponseSerializer(serializers.ModelSerializer):
    """Serializer for registration response (excludes sensitive fields)"""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'first_name', 'last_name', 'full_name',
            'user_type', 'preferred_language', 'email_verified', 'phone_verified',
            'date_joined'
        ]
        read_only_fields = fields


class VerifyPhoneResponseSerializer(serializers.Serializer):
    """Serializer for phone verification response"""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    phone_verified = serializers.BooleanField()
    user_fully_verified = serializers.BooleanField()
    user = UserProfileSerializer(read_only=True, required=False)


class VerifyEmailResponseSerializer(serializers.Serializer):
    """Serializer for email verification response"""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    access_token = serializers.CharField(required=False)
    refresh_token = serializers.CharField(required=False)
    verification_complete = serializers.BooleanField()
    user = UserProfileSerializer(read_only=True, required=False)


class VerificationStatusSerializer(serializers.Serializer):
    """Serializer for verification status endpoint"""
    
    email_verified = serializers.BooleanField()
    phone_verified = serializers.BooleanField()
    fully_verified = serializers.BooleanField()
    can_login = serializers.BooleanField()


class EmailAvailabilitySerializer(serializers.Serializer):
    """Serializer for email availability check"""
    
    email = serializers.EmailField()


class PhoneAvailabilitySerializer(serializers.Serializer):
    """Serializer for phone availability check"""
    
    phone_number = serializers.CharField(max_length=20, required=False)


class ResendEmailVerificationSerializer(serializers.Serializer):
    """Serializer for resending email verification"""
    
    email = serializers.EmailField(required=False)
    user_id = serializers.UUIDField(required=False)

    def validate(self, attrs):
        """Validate that either email or user_id is provided"""
        if not attrs.get('email') and not attrs.get('user_id'):
            raise serializers.ValidationError("Either email or user_id is required")
        return attrs


class LoginResponseSerializer(serializers.Serializer):
    """Serializer for login response"""
    
    success = serializers.BooleanField()
    access_token = serializers.CharField(required=False)
    refresh_token = serializers.CharField(required=False)
    temporary_token = serializers.CharField(required=False)
    user = UserProfileSerializer(required=False)
    message = serializers.CharField()
    requires_verification = serializers.BooleanField(required=False)
    verification_type = serializers.CharField(required=False)
    user_id = serializers.UUIDField(required=False)
    email = serializers.EmailField(required=False)
    next_step = serializers.CharField(required=False)
    verification_status = serializers.DictField(required=False)


class PasswordResetResponseSerializer(serializers.Serializer):
    """Serializer for password reset response"""
    
    message = serializers.CharField()
    success = serializers.BooleanField(required=False)


class ChangePasswordResponseSerializer(serializers.Serializer):
    """Serializer for change password response"""
    
    message = serializers.CharField()
    success = serializers.BooleanField()


class UserProfileResponseSerializer(serializers.Serializer):
    """Serializer for user profile response"""
    
    success = serializers.BooleanField()
    data = UserProfileSerializer(required=False)
    message = serializers.CharField(required=False)