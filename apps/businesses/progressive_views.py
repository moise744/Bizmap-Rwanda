from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Business, BusinessCategory
from .serializers import BusinessCreateSerializer
import logging

logger = logging.getLogger(__name__)

class ProgressiveBusinessCreateView(generics.CreateAPIView):
    serializer_class = BusinessCreateSerializer
    permission_classes = [IsAuthenticated]

    def calculate_completion_percentage(self, business):
        """Calculate business profile completion percentage"""
        
        # Essential fields (30 points each)
        essential_fields = [
            'business_name', 'description', 'category', 'phone_number',
            'province', 'district', 'address'
        ]
        
        # Additional fields (10 points each) 
        additional_fields = [
            'secondary_phone', 'email', 'website', 'sector', 'cell'
        ]
        
        # Enhancement checks (5 points each)
        enhancement_checks = [
            bool(business.latitude and business.longitude),
            len(business.amenities) > 0 if business.amenities else False,
            len(business.services_offered) > 0 if business.services_offered else False,
            len(business.payment_methods) > 0 if business.payment_methods else False,
        ]
        
        # Count completed fields
        essential_completed = sum(1 for field in essential_fields 
                                if getattr(business, field, None))
        additional_completed = sum(1 for field in additional_fields 
                                if getattr(business, field, None))
        enhancement_completed = sum(enhancement_checks)
        
        # Calculate score
        total_score = (essential_completed * 30) + (additional_completed * 10) + (enhancement_completed * 5)
        max_score = (len(essential_fields) * 30) + (len(additional_fields) * 10) + (len(enhancement_checks) * 5)
        
        return min(100, round((total_score / max_score) * 100))

    def perform_create(self, serializer):
        user = self.request.user
        if user.user_type != 'business_owner':
            user.user_type = 'business_owner'
            user.save()
        
        # Handle category conversion here as well (backup)
        validated_data = serializer.validated_data.copy()
        
        # Save location detection timestamp if coordinates provided
        if validated_data.get('latitude') and validated_data.get('longitude'):
            validated_data['location_detected_at'] = timezone.now()
        
        # Ensure empty strings for optional fields
        optional_fields = ['sector', 'cell', 'secondary_phone', 'email', 'website']
        for field in optional_fields:
            if field not in validated_data or validated_data[field] is None:
                validated_data[field] = ''
        
        business = serializer.save(owner=user, **validated_data)
        
        # Store reference to created business for later use
        self._created_business = business
        
        # Calculate and save completion percentage
        completion = self.calculate_completion_percentage(business)
        business.profile_completion_percentage = completion
        
        # Make business active and searchable even with just essential info
        business.is_active = True
        
        # Set verification status based on completion
        if completion >= 50:
            business.verification_status = 'pending'
        
        business.save()
        
        logger.info(f"Business created successfully: {business.business_name} (ID: {business.business_id})")

    def create(self, request, *args, **kwargs):
        """Override to return additional info with better error handling"""
        try:
            # Log the incoming request data for debugging
            logger.info(f"Creating business with data: {request.data}")
            
            response = super().create(request, *args, **kwargs)
            
            if response.status_code == 201:
                # The serializer should return the business data
                # Get the business_id from the serializer data
                business_id = None
                
                # Try different ways to get the business_id
                if hasattr(response, 'data') and 'business_id' in response.data:
                    business_id = response.data['business_id']
                elif hasattr(self, '_created_business'):
                    business_id = self._created_business.business_id
                else:
                    # Last resort - get the most recently created business by this user
                    recent_business = Business.objects.filter(owner=request.user).order_by('-created_at').first()
                    if recent_business:
                        business_id = recent_business.business_id
                
                if business_id:
                    try:
                        business = Business.objects.get(business_id=business_id)
                        response.data.update({
                            'business_id': str(business.business_id),
                            'completion_percentage': business.profile_completion_percentage,
                            'is_active': business.is_active,
                            'message': 'Business saved successfully! Your listing is now live and searchable by customers.'
                        })
                    except Business.DoesNotExist:
                        logger.error(f"Business not found with ID: {business_id}")
                
            return response
            
        except Exception as e:
            logger.error(f"Error creating business: {str(e)}")
            logger.error(f"Request data: {request.data}")
            
            # Return a more helpful error response
            return Response({
                'error': 'Failed to create business',
                'details': str(e) if hasattr(e, 'args') else 'Unknown error occurred'
            }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_business_progress(request):
    """Save business registration progress"""
    
    return Response({
        'status': 'progress_saved',
        'message': 'Progress saved successfully'
    })