from django.http import JsonResponse
from django.conf import settings
from django.db import connection
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    try:
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        return JsonResponse({
            "status": "healthy",
            "database": "connected"
        })
    except Exception as e:
        return JsonResponse({
            "status": "unhealthy", 
            "database": "disconnected",
            "error": str(e)
        }, status=503)


@csrf_exempt
@require_http_methods(["GET"])
def app_config(request):
    return JsonResponse({
        "new_release": settings.APP_NEW_RELEASE,
        "new_release_code": settings.APP_NEW_RELEASE_CODE,
        "new_release_description": settings.APP_NEW_RELEASE_DESCRIPTION,
        "alternative_map": settings.APP_ALTERNATIVE_MAP,
        "alternative_map_url": settings.APP_ALTERNATIVE_MAP_URL if settings.APP_ALTERNATIVE_MAP else "",
    })
