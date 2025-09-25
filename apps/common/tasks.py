from celery import shared_task
import time
from django.core.cache import cache

@shared_task
def test_redis_connection():
    """Test if Celery can connect to Redis"""
    # Test Redis cache
    cache.set('celery_test', 'success', 300)
    result = cache.get('celery_test')
    
    # Test simple task execution
    time.sleep(2)  # Simulate work
    
    return {
        'status': 'SUCCESS',
        'redis_connection': 'working' if result == 'success' else 'failed',
        'message': 'Celery + Redis are working locally!'
    }

@shared_task
def add_numbers(x, y):
    """Simple math task to test Celery"""
    result = x + y
    print(f"Adding {x} + {y} = {result}")
    return result

@shared_task
def process_business_data(business_id):
    """Simulate a real task you might use"""
    print(f"Processing business data for ID: {business_id}")
    # Simulate some work
    time.sleep(3)
    return f"Processed business {business_id}"