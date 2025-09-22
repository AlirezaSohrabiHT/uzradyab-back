# otpmanager/utils.py (new file for helpers)

import random
from datetime import timedelta
from django.utils.timezone import now
from kavenegar import KavenegarAPI, APIException, HTTPException
from django.conf import settings
from .models import OTP


def send_otp(phone_number: str):
    """Generate and send OTP to given phone number."""
    if not phone_number or not phone_number.isdigit() or len(phone_number) < 10:
        return False, "شماره تلفن نامعتبر است."

    try:
        otp_code = str(random.randint(100000, 999999))

        OTP.objects.update_or_create(
            phone=phone_number,
            defaults={"otp_code": otp_code, "created_at": now()}
        )

        api = KavenegarAPI(settings.KAVENEGAR_API_KEY)
        params = {
            "receptor": phone_number,
            "template": "uzradyab",
            "token": otp_code,
            "type": "sms",
        }
        api.verify_lookup(params)

        return True, "کد تایید ارسال شد."
    except (APIException, HTTPException):
        return False, "ارسال کد با مشکل مواجه شده است."


def verify_otp(phone_number: str, otp_code: str):
    """Check if OTP is valid for given phone number."""
    otp_instance = OTP.objects.filter(phone=phone_number, otp_code=otp_code).first()

    if not otp_instance:
        return False, "کد تایید نادرست است."

    if now() > otp_instance.created_at + timedelta(minutes=5):
        return False, "کد تایید منقضی شده است."

    return True, "OK"
