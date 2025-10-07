
# otpmanager/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

from .utils import send_otp as send_otp_helper, verify_otp as verify_otp_helper


@csrf_exempt
@require_POST
def send_otp(request):
    """API endpoint for sending OTP."""
    try:
        data = json.loads(request.body.decode('utf-8'))
        phone_number = data.get("phone")
    except Exception:
        return JsonResponse({"success": False, "message": "داده نامعتبر است."}, status=400)

    success, message = send_otp_helper(phone_number)
    return JsonResponse({"success": success, "message": message},
                        status=200 if success else 400)


@csrf_exempt
@require_POST
def verify_otp(request):
    """API endpoint for verifying OTP."""
    try:
        data = json.loads(request.body.decode('utf-8'))
        phone_number = data.get("phone")
        otp_code = data.get("otp")
    except Exception:
        return JsonResponse({"success": False, "message": "داده نامعتبر است."}, status=400)

    success, message = verify_otp_helper(phone_number, otp_code)
    return JsonResponse({"success": success, "message": message},
                        status=200 if success else 400)

