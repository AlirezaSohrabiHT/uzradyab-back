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
from django.contrib.auth.hashers import check_password
import re
from django.contrib.auth import get_user_model
import requests

User = get_user_model()

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
    user = request.user

    return Response({
    'phone': user.phone,
    'credit': user.credit,
    'last_login': user.last_login
    }, status = status.HTTP_200_OK)

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