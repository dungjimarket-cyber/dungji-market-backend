"""
Health check API views
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.utils import timezone


@api_view(['GET'])
def health_check(request):
    """
    Simple health check endpoint for deployment monitoring
    """
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Prepare response data
    health_data = {
        "status": "healthy" if db_status == "ok" else "unhealthy",
        "timestamp": timezone.now().isoformat(),
        "database": db_status,
        "version": "1.0.1",  # Updated to verify deployment
        "google_search_proxy_available": True  # Indicator that google_search_proxy should be available
    }
    
    # Return 200 if healthy, 503 if unhealthy
    response_status = status.HTTP_200_OK if db_status == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return Response(health_data, status=response_status)