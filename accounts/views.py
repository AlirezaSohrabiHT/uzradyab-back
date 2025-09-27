from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from datetime import timedelta
from django.utils.timezone import now
from django.contrib.auth.hashers import check_password
import re
from django.contrib.auth import get_user_model
import requests
import logging
from otpmanager.models import OTP
from otpmanager.views import send_otp, verify_otp

auth_logger = logging.getLogger('authlogs')

User = get_user_model()

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_auth_attempt(event_type, phone_number, success, details=None, request=None, user_id=None):
    """
    Log authentication attempts with detailed information
    
    Args:
        event_type: 'login', 'signup', 'reset_password', 'otp_send', 'otp_verify'
        phone_number: User's phone number
        success: Boolean indicating success/failure
        details: Additional details (error message, etc.)
        request: Django request object for IP tracking
        user_id: User ID if available
    """
    client_ip = get_client_ip(request) if request else 'Unknown'
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown') if request else 'Unknown'
    
    log_data = {
        'event': event_type,
        'phone_number': phone_number,
        'success': success,
        'ip_address': client_ip,
        'user_agent': user_agent,
        'user_id': user_id,
        'timestamp': now().isoformat(),
        'details': details or {}
    }
    
    if success:
        auth_logger.info(f"SUCCESS - {event_type.upper()} | Phone: {phone_number} | IP: {client_ip} | User ID: {user_id}")
    else:
        auth_logger.warning(f"FAILED - {event_type.upper()} | Phone: {phone_number} | IP: {client_ip} | Error: {details} | User Agent: {user_agent}")


def create_standard_response(success=True, message="", data=None, errors=None):
    """Create standardized API response"""
    response_data = {
        "success": success,
        "message": message
    }
    
    if data:
        response_data.update(data)
    
    if errors:
        response_data["errors"] = errors
    
    return response_data


def validate_and_normalize_phone(phone):
    """Validate and normalize phone number to standard format"""
    if not phone:
        return None

    phone = str(phone).strip()

    # Normalize to "09..."
    if phone.startswith("+98"):
        phone = "0" + phone[3:]
    elif phone.startswith("98"):
        phone = "0" + phone[2:]
    elif phone.startswith("9") and len(phone) == 10:
        phone = "0" + phone

    # Validate after normalization
    if re.fullmatch(r"^09\d{9}$", phone):
        return phone

    return None


# FBV api
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request):
    """Get current user information"""
    user = request.user

    try:
        return Response(
            create_standard_response(True, "User information retrieved successfully.", {
            'phone': user.phone,
            'credit': user.credit,
            'last_login': user.last_login
            }),
            status=status.HTTP_200_OK
        )

    except Exception as e:
        auth_logger.error(f"Error retrieving user info: {e}")
        return Response(
            create_standard_response(False, "خطا در دریافت اطلاعات کاربر."),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_balance(request):
    """Get current user balance"""
    user = request.user
    
    try:
        return Response(
            create_standard_response(True, "Balance retrieved successfully.", {
                "balance": user.credit
            }),
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        auth_logger.error(f"Error retrieving user balance: {e}")
        return Response(
            create_standard_response(False, "خطا در دریافت موجودی."),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def edit_profile(request):
    """Edit user profile information"""
    user = request.user

    new_phone = request.data.get('phone')

    try:
        # Validate national code uniqueness
        if new_phone is not None:
            if not validate_and_normalize_phone(new_phone):
                return Response(
                    "شماره تلفن وارد شده نامعتبر است.",
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if User.objects.filter(phone=new_phone).exclude(id=user.id).exists():
                return Response(
                    "کاربری با این شماره تلفن وجود دارد.",
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Update fields if provided
        if new_phone is not None:
            user.phone = new_phone

        # Validate and save
        user.full_clean()
        user.save()

        return Response(
            "پروفایل با موفقیت به‌روزرسانی شد.",
            status=status.HTTP_200_OK
        )

    except ValidationError as e:
        return Response(
            "اطلاعات وارد شده نامعتبر است." ,
            status=status.HTTP_400_BAD_REQUEST
        )

    except IntegrityError as e:
        return Response(
            "خطا در به‌روزرسانی پروفایل.",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    except Exception as e:
        return Response(
            "خطای غیرمنتظره رخ داده است.",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def reset_password(request):
    """
    Multi-step password reset process:
    1. Send OTP to phone number
    2. Verify OTP
    3. Set new password
    """
    phone_number = validate_and_normalize_phone(request.data.get('phoneNumber'))
    otp_code = request.data.get('otp')
    new_password = request.data.get('newPassword')

    if not phone_number:
        log_auth_attempt('reset_password', phone_number or 'INVALID', False, 
                        'Invalid phone number format')
        return Response(
            create_standard_response(False, "فرمت شماره تلفن وارد شده صحیح نیست."),
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        customer = User.objects.get(phone=phone_number)
    except User.DoesNotExist:
        log_auth_attempt('reset_password', phone_number, False, 'User not found')
        return Response(
            create_standard_response(False, "کاربری با این شمارۀ تلفن یافت نشد."),
            status=status.HTTP_404_NOT_FOUND
        )

    # Step 2: Verify OTP
    if otp_code:
        verified, message = verify_otp(phone_number, otp_code)

        if not verified:
            log_auth_attempt('reset_password', phone_number, False, 
                            f'OTP verification failed: {message}', user_id=customer.id)
            return Response(
                create_standard_response(False, message),
                status=status.HTTP_401_UNAUTHORIZED
            )

        log_auth_attempt('reset_password', phone_number, True, 
                        'OTP verified successfully', user_id=customer.id)
        return Response(
            create_standard_response(True, "کد وارد شده تایید شد.", {"user_id": customer.id}),
            status=status.HTTP_200_OK
        )

    # Step 3: Set new password
    elif new_password:
        customer.set_password(new_password)
        customer.save()

        OTP.objects.filter(phone=phone_number).delete()
        log_auth_attempt('reset_password', phone_number, True, 
                        'Password reset completed successfully', user_id=customer.id)
        return Response(
            create_standard_response(True, "رمز عبور با موفقیت تغییر یافت."),
            status=status.HTTP_200_OK
        )

    # Step 1: Send OTP
    else:
        success, msg = send_otp(phone_number)

        if not success:
            return Response(
                create_standard_response(False, msg),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            create_standard_response(True, msg, {"otp_sent": True}),
            status=status.HTTP_200_OK
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    user = request.user
    current_password = request.data.get('currentPassword')
    new_password = request.data.get('newPassword')

    # Input validation - removed length check, only check for existence
    if not current_password or not new_password:
        return Response(
            "رمز عبور فعلی و جدید الزامی هستند.",
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Verify current password
        if not check_password(current_password, user.password):
            return Response(
                "رمز عبور فعلی نادرست است.",
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password - no length validation
        user.set_password(new_password)
        user.save()

        return Response(
            "رمز عبور با موفقیت تغییر یافت.",
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            "خطا در تغییر رمز عبور.",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class LoginView(APIView):
    def post(self, request):
        phone = request.data.get('phone')
        password = request.data.get('password')

        if not phone or not password:
            return Response({'error': 'Phone and password are required.'}, status=400)

        user = authenticate(request, username=phone, password=password)
        if not user:
            return Response({'error': 'Invalid credentials'}, status=401)

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            'token': token.key,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'traccar_id': user.traccar_id,
            'id': user.id
        }, status=200)


class GenerateTraccarTokenView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        username = user.phone
        password = request.data.get('password')

        if not password:
            return Response({"error": "Password is required."}, status=400)

        expiration = (timezone.now() + timedelta(days=365)).isoformat()

        # Step 1: Get token
        token_url = "https://app.uzradyab.ir/api/session/token"
        token_response = requests.post(
            token_url,
            auth=requests.auth.HTTPBasicAuth(username, password),
            data={'expiration': expiration}
        )

        if token_response.status_code != 200:
            return Response({
                "error": f"Error generating token: {token_response.status_code}",
                "details": token_response.text
            }, status=token_response.status_code)

        token = token_response.text.strip()
        if not token:
            return Response({"error": "Empty token received."}, status=400)

        # Step 2: Get session info by POST to /session (as login)
        session_url = "https://app.uzradyab.ir/api/session"
        session_response = requests.post(
            session_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"email": username, "password": password}
        )

        if session_response.status_code != 200:
            return Response({
                "error": f"Failed to fetch session info: {session_response.status_code}",
                "details": session_response.text
            }, status=session_response.status_code)

        session_data = session_response.json()
        traccar_id = session_data.get("id")

        if not traccar_id:
            return Response({"error": "No user ID found in session data."}, status=500)

        # Step 3: Save both to user
        user.traccar_token = token
        user.traccar_id = traccar_id
        user.save()

        return Response({
            "message": "Token and Traccar ID successfully saved.",
            "token": token,
            "traccar_id": traccar_id
        }, status=200)
        
class CheckTraccarTokenView(APIView):
    authentication_classes = [TokenAuthentication]  # Token-based authentication
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    def get(self, request):
        # The authenticated user is now available as `request.user`
        user = request.user
        
        # Check if the user has a Traccar token
        if user.traccar_token:
            return Response({"message": "User has a Traccar token."}, status=200)
        else:
            return Response({"message": "User does not have a Traccar token."}, status=200)