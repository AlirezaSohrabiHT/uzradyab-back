from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now
import json
import random
from kavenegar import KavenegarAPI, APIException, HTTPException
from django.conf import settings
from .models import OTP
from datetime import timedelta

@csrf_exempt
def send_otp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            phone_number = data.get("phone")

            if not phone_number or not phone_number.isdigit() or len(phone_number) < 10:
                return JsonResponse({"error": "Invalid phone number"}, status=400)

            # Generate a new OTP
            otp_code = str(random.randint(100000, 999999))

            # Store the OTP in the database
            otp_instance, created = OTP.objects.update_or_create(
                phone=phone_number,
                defaults={"otp_code": otp_code, "created_at": now()}
            )

            # Send the OTP via SMS
            api = KavenegarAPI('415270574F5349545265306244503252575A44584C52614C69736C6C56437841')
            params = {
                "receptor": phone_number,
                "template": "uzradyab",  # Replace with your actual Kavenegar template
                "token": otp_code,
                "type": "sms",
            }

            response = api.verify_lookup(params)

            return JsonResponse({"message": "OTP sent successfully"})

        except (APIException, HTTPException) as e:
            return JsonResponse({"error": f"ارسال کد با مشکل مواجه شده است."}, status=500)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON input"}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def verify_otp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            phone_number = data.get("phone")
            otp_code = data.get("otp")

            if not phone_number or not otp_code:
                return JsonResponse({"error": "Invalid phone number or OTP"}, status=400)

            # Retrieve the OTP entry from the database
            otp_instance = OTP.objects.filter(phone=phone_number, otp_code=otp_code).first()

            if not otp_instance:
                return JsonResponse({"error": "OTP is incorrect"}, status=400)

            # Check if OTP is expired (valid for 5 minutes)
            otp_expiry_time = otp_instance.created_at + timedelta(minutes=5)
            if now() > otp_expiry_time:
                return JsonResponse({"error": "OTP has expired"}, status=400)

            # OTP is valid, return success response
            return JsonResponse({"message": "OK"})  # Only returning "OK"

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON input"}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)