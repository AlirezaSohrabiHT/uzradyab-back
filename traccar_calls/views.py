import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from dateutil import parser
from django.utils import timezone
import requests
import logging
from django.db import connections
from django.conf import settings
from rest_framework.pagination import PageNumberPagination
from datetime import datetime, timedelta
from django.utils.timezone import make_aware
from rest_framework import generics
import requests
from rest_framework.response import Response

logger = logging.getLogger('main')

class TraccarSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        url = f"{settings.TRACCAR_API_URL}/session"

        payload = {
            "email": user.phone,  # or map phone to email if needed
            "password": user.raw_password
        }

        try:
            r = requests.post(url, json=payload)
            if r.status_code == 200:
                return Response(r.json(), status=200)
            return Response({"detail": r.text}, status=r.status_code)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class DevicePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'

class FetchDevicesView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = DevicePagination

    def get(self, request):
        user = request.user
        base_url = settings.TRACCAR_API_URL
        url = f"{base_url}/devices"

        headers = {
            "Authorization": f"Bearer {user.traccar_token}"
        }

        try:
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                return Response({
                    "error": "Failed to fetch devices.",
                    "details": response.text
                }, status=response.status_code)

            devices = response.json()

            # 🔍 فیلتر محلی بر اساس search query
            search = request.query_params.get('search')
            if search:
                search = search.lower()
                devices = [
                    d for d in devices
                    if search in d.get('name', '').lower() or
                       search in d.get('uniqueId', '').lower()
                ]

            # 🔍 status filter (active, inactive, expired)
            status = request.query_params.get('status')
            if status:
                now = timezone.now()  # always aware datetime

                if status == "active":
                    devices = [d for d in devices if d.get('status') == "online"]

                elif status == "inactive":
                    devices = [d for d in devices if d.get('status') == "offline"]

                elif status == "expired":
                    devices = [
                        d for d in devices
                        if d.get("expirationTime") and parser.isoparse(d["expirationTime"]) < now
                    ]

            # 📄 صفحه‌بندی محلی
            paginated = self.paginate_queryset(devices)
            return self.get_paginated_response(paginated)

        except Exception as e:
            return Response({"error": str(e)}, status=500)
        
class UpdateDeviceView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, device_id):
        user = request.user
        base_url = settings.TRACCAR_API_URL
        url = f"{base_url}/devices/{device_id}"

        headers = {
            "Authorization": f"Bearer {user.traccar_token}"
        }

        try:
            data = request.data
            response = requests.put(url, json=data, headers=headers)

            if response.status_code == 200:
                return Response(response.json(), status=200)
            else:
                return Response({
                    "error": "Failed to update device.",
                    "status_code": response.status_code,
                    "details": response.text
                }, status=response.status_code)

        except Exception as e:
            return Response({"error": str(e)}, status=500)        

class FetchDriversView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        base_url = settings.TRACCAR_API_URL
        url = f"{base_url}/drivers"

        # Collect query parameters
        allowed_params = ["all", "userId", "deviceId", "groupId", "refresh"]
        params = {}

        for param in allowed_params:
            if param in request.query_params:
                # For list parameters like deviceId, groupId
                if param in ["deviceId", "groupId"]:
                    values = request.query_params.getlist(param)
                    if values:
                        params[param] = values
                # For boolean parameters like all, refresh
                elif param in ["all", "refresh"]:
                    value = request.query_params.get(param)
                    if value.lower() in ['true', '1', 'yes']:
                        params[param] = 'true'
                    elif value.lower() in ['false', '0', 'no']:
                        params[param] = 'false'
                # For single value parameters like userId
                else:
                    value = request.query_params.get(param)
                    if value:
                        params[param] = value

        headers = {
            "Authorization": f"Bearer {user.traccar_token}"
        }

        try:
            response = requests.get(
                url,
                params=params,
                headers=headers
            )

            if response.status_code == 200:
                return Response(response.json(), status=200)
            else:
                return Response({
                    "error": "Failed to fetch drivers from Traccar.",
                    "status_code": response.status_code,
                    "details": response.text,
                }, status=response.status_code)

        except Exception as e:
            return Response({
                "error": f"An error occurred while fetching drivers: {str(e)}",
                "status_code": 500
            }, status=500)
            

# class FetchUsersView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         user = request.user
#         base_url = settings.TRACCAR_API_URL
#         url = f"{base_url}/users"

#         # Prepare query params
#         params = {}
#         if 'userId' in request.query_params:
#             params['userId'] = request.query_params.get('userId')

#         # Prepare authorization header using Bearer token
#         headers = {
#             "Authorization": f"Bearer {user.traccar_token}"
#         }

#         try:
#             response = requests.get(
#                 url,
#                 params=params,
#                 headers=headers
#             )

#             if response.status_code == 200:
#                 return Response(response.json(), status=200)
#             else:
#                 return Response({
#                     "error": "Failed to fetch users from Traccar.",
#                     "status_code": response.status_code,
#                     "details": response.text,
#                 }, status=response.status_code)

#         except Exception as e:
#             return Response({
#                 "error": f"An error occurred while fetching users: {str(e)}",
#                 "status_code": 500
#             }, status=500)
            
class UserPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'

class FetchUsersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        base_url = settings.TRACCAR_API_URL
        url = f"{base_url}/users"

        headers = {
            "Authorization": f"Bearer {user.traccar_token}"
        }

        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return Response({
                    "error": "Failed to fetch users.",
                    "details": response.text
                }, status=response.status_code)

            users = response.json()

            # 🔍 فیلتر کردن بر اساس search (نام، ایمیل یا شماره)
            search = request.query_params.get('search', '').lower()
            if search:
                users = [
                    u for u in users
                    if search in (u.get('name') or '').lower()
                    or search in (u.get('email') or '').lower()
                    or search in (u.get('phone') or '').lower()
                ]

            # فیلتر دیگر مانند administrator
            admin_filter = request.query_params.get('administrator')
            if admin_filter in ['true', 'false']:
                is_admin = admin_filter == 'true'
                users = [u for u in users if u.get('administrator') == is_admin]

            # صفحه‌بندی محلی
            paginator = UserPagination()
            result_page = paginator.paginate_queryset(users, request)
            return paginator.get_paginated_response(result_page)

        except Exception as e:
            return Response({"error": str(e)}, status=500)
 
class UpdateTraccarUserView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, user_id):
        base_url = settings.TRACCAR_API_URL
        url = f"{base_url}/users/{user_id}"

        headers = {
            "Authorization": f"Bearer {request.user.traccar_token}"
        }

        data = request.data  # فرض می‌کنیم فرم کلاینت همه فیلدهای لازم را ارسال می‌کند

        try:
            response = requests.put(url, json=data, headers=headers)

            if response.status_code == 200:
                return Response(response.json(), status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": "Failed to update user.",
                    "status_code": response.status_code,
                    "details": response.text
                }, status=response.status_code)

        except Exception as e:
            return Response({
                "error": f"An error occurred while updating user: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
class FetchStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        base_url = settings.TRACCAR_API_URL
        url = f"{base_url}/statistics"

        try:
            # Handle date range from query params or fallback to last 7 days
            from_date = request.query_params.get('from')
            if not from_date:
                from_date = (datetime.now() - timedelta(days=7)).isoformat() + 'Z'

            to_date = request.query_params.get('to')
            if not to_date:
                to_date = datetime.now().isoformat() + 'Z'

            params = {
                'from': from_date,
                'to': to_date
            }

            headers = {
                "Authorization": f"Bearer {user.traccar_token}"
            }

            response = requests.get(
                url,
                params=params,
                headers=headers
            )

            if response.status_code == 200:
                return Response(response.json(), status=200)
            else:
                return Response({
                    "error": "Failed to fetch statistics from Traccar.",
                    "status_code": response.status_code,
                    "details": response.text,
                }, status=response.status_code)

        except Exception as e:
            return Response({
                "error": f"An error occurred while fetching statistics: {str(e)}",
                "status_code": 500
            }, status=500)

class CreateTraccarUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        url = f"{settings.TRACCAR_API_URL}/users"
        headers = {
            "Authorization": f"Bearer {request.user.traccar_token}"
        }

        try:
            response = requests.post(url, json=request.data, headers=headers)
            if response.status_code == 200:
                return Response(response.json(), status=200)
            return Response({
                "error": "Failed to create user",
                "details": response.text
            }, status=response.status_code)

        except Exception as e:
            return Response({"error": str(e)}, status=500)
 

class CreateDeviceAndUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        base_url = settings.TRACCAR_API_URL
        auth_header = {
            "Authorization": f"Bearer {user.traccar_token}"
        }

        data = request.data
        device_data = data.get("device")
        user_data = data.get("user")

        if not device_data or not user_data:
            return Response({"error": "Both 'device' and 'user' data are required."}, status=400)

        unique_id = device_data.get("uniqueId")

        try:
            # Step 1: Check if device exists
            check_device_url = f"{base_url}/devices"
            params = {"uniqueId": unique_id}
            response = requests.get(check_device_url, headers=auth_header, params=params)

            if response.status_code != 200:
                return Response({
                    "error": "Failed to check device existence.",
                    "details": response.text
                }, status=response.status_code)

            existing_devices = response.json()
            if existing_devices:
                return Response({
                    "error": f"Device with uniqueId '{unique_id}' already exists."
                }, status=409)

            # Step 2: Create user
            create_user_url = f"{base_url}/users"
            response = requests.post(create_user_url, headers=auth_header, json=user_data)

            if response.status_code != 200:
                return Response({
                    "error": "Failed to create user.",
                    "details": response.text
                }, status=response.status_code)

            created_user = response.json()
            created_user_id = created_user.get("id")

            # Step 3: Create device
            create_device_url = f"{base_url}/devices"
            response = requests.post(create_device_url, headers=auth_header, json=device_data)

            if response.status_code != 200:
                return Response({
                    "error": "Failed to create device.",
                    "details": response.text
                }, status=response.status_code)

            created_device = response.json()
            created_device_id = created_device.get("id")

            # Step 4: Link user and device
            permission_url = f"{base_url}/permissions"
            link_payload = {
                "userId": created_user_id,
                "deviceId": created_device_id
            }

            response = requests.post(permission_url, headers=auth_header, json=link_payload)

            if response.status_code != 200:
                return Response({
                    "error": "Failed to link user to device.",
                    "details": response.text
                }, status=response.status_code)

            # ✅ Success
            return Response({
                "message": "User, device created and linked successfully.",
                "user": created_user,
                "device": created_device
            }, status=201)

        except Exception as e:
            logger.error(f"CreateDeviceAndUserView error: {str(e)}")
            return Response({"error": str(e)}, status=500)
                
class CreateTraccarDeviceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        url = f"{settings.TRACCAR_API_URL}/devices"
        headers = {
            "Authorization": f"Bearer {request.user.traccar_token}"
        }

        try:
            response = requests.post(url, json=request.data, headers=headers)
            if response.status_code == 200:
                device_data = response.json()
                return Response({
                    "message": "Device created successfully.",
                    "device_id": device_data.get("id"),
                    "device": device_data  # optionally include full device info
                }, status=200)

            return Response({
                "error": "Failed to create device",
                "details": response.text
            }, status=response.status_code)

        except Exception as e:
            return Response({"error": str(e)}, status=500)
              
class DeviceUsersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get all users connected to a specific device directly from the database.
        
        Process:
        1. Get device ID from query parameters
        2. Connect to second database and query the tc_user_device table
        3. Get user IDs associated with the device
        4. For each user ID, fetch the user details from Traccar API
        5. Return the list of user details
        """
        device_id = request.query_params.get('deviceId')
        
        if not device_id:
            return Response({"error": "Device ID is required"}, status=400)
        
        try:
            # Step 1: Query the second database to get user IDs
            user_ids = self._get_user_ids_for_device(device_id)
            
            if not user_ids:
                return Response([], status=200)
            
            # Step 2: Fetch user details from Traccar API for each user ID
            users = []
            
            for user_id in user_ids:
                user_details = self._get_user_details(user_id)
                if user_details:
                    users.append(user_details)
            
            return Response(users, status=200)
            
        except Exception as e:
            logger.error(f"Error in DeviceUsersView: {str(e)}")
            return Response({"error": f"An error occurred: {str(e)}"}, status=500)
    
    def _get_user_ids_for_device(self, device_id):
        """Query the second database to get user IDs for a specific device."""
        user_ids = []
        
        with connections['device_user_db'].cursor() as cursor:
            # Execute SQL query exactly as specified
            cursor.execute("SELECT userid FROM tc_user_device WHERE deviceid = %s", [device_id])
            rows = cursor.fetchall()
            
            # Extract user IDs from query results
            for row in rows:
                user_ids.append(row[0])  # First column contains the user ID
        
        return user_ids
    
    def _get_user_details(self, user_id):
        """Fetch user details from Traccar API for a specific user ID using Bearer token."""
        base_url = settings.TRACCAR_API_URL
        token = self.request.user.traccar_token  # <- استفاده از توکن

        try:
            url = f"{base_url}/users/{user_id}"
            headers = {
                "Authorization": f"Bearer {token}"
            }

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch user {user_id}: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {str(e)}")
            return None

class LinkUserToDeviceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.data.get('userId')
        device_id = request.data.get('deviceId')

        if not user_id or not device_id:
            return Response({"error": "Both userId and deviceId are required."}, status=400)

        token = request.user.traccar_token
        url = f"{settings.TRACCAR_API_URL}/permissions"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        data = {
            "userId": user_id,
            "deviceId": device_id
        }

        try:
            response = requests.post(url, json=data, headers=headers)

            if response.status_code == 200:
                return Response({"success": "User linked to device successfully"}, status=200)
            else:
                logger.warning(f"Failed to link: {response.status_code} - {response.text}")
                return Response({"error": "Failed to link user and device", "details": response.text}, status=response.status_code)

        except Exception as e:
            logger.error(f"Error linking user to device: {str(e)}")
            return Response({"error": str(e)}, status=500)
        
class ChangeUserPasswordView(APIView):
    # permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Change user password by phone number.
        
        Expected payload:
        {
            "phone": "user_phone_number",
            "password": "new_password"
        }
        """
        phone = request.data.get('phone')
        new_password = request.data.get('password')

        if not phone or not new_password:
            return Response({
                "error": "Both 'phone' and 'password' are required."
            }, status=400)

        base_url = settings.TRACCAR_API_URL
        
        # Basic Auth credentials (static)
        auth = (settings.TRACCAR_API_USERNAME, settings.TRACCAR_API_PASSWORD)

        try:
            # Step 1: Fetch all users to find the one with matching email (phone)
            users_url = f"{base_url}/users"
            response = requests.get(users_url, auth=auth)

            if response.status_code != 200:
                return Response({
                    "error": "Failed to fetch users from Traccar.",
                    "status_code": response.status_code,
                    "details": response.text
                }, status=response.status_code)

            users = response.json()

            # Step 2: Find user where email matches phone
            target_user = None
            for user in users:
                if user.get('email') == phone:
                    target_user = user
                    break

            if not target_user:
                return Response({
                    "error": f"No user found with email matching phone number: {phone}"
                }, status=404)

            user_id = target_user.get('id')

            # Step 3: Update the user's password
            update_url = f"{base_url}/users/{user_id}"
            
            # Prepare the user data with updated password
            # Keep all existing user data and only update the password
            user_data = target_user.copy()
            user_data['password'] = new_password

            response = requests.put(update_url, json=user_data, auth=auth)

            if response.status_code == 200:
                # Don't return the password in the response for security
                updated_user = response.json()
                if 'password' in updated_user:
                    del updated_user['password']
                
                return Response({
                    "message": "Password updated successfully.",
                    "user": updated_user
                }, status=200)
            else:
                return Response({
                    "error": "Failed to update user password.",
                    "status_code": response.status_code,
                    "details": response.text
                }, status=response.status_code)

        except Exception as e:
            logger.error(f"ChangeUserPasswordView error: {str(e)}")
            return Response({
                "error": f"An error occurred while changing password: {str(e)}"
            }, status=500)
            
class CheckUserExistsView(APIView):
    def get(self, request):
        """
        Check if a user exists with the given phone number.
        Uses the same approach as ChangeUserPasswordView that works perfectly.
        
        Query parameter: phone
        Returns: {"exists": true/false}
        """
        phone = request.query_params.get('phone')
        
        if not phone:
            return Response({"error": "Phone parameter is required"}, status=400)

        base_url = settings.TRACCAR_API_URL
        
        # Basic Auth credentials (static) - same as ChangeUserPasswordView
        auth = (settings.TRACCAR_API_USERNAME, settings.TRACCAR_API_PASSWORD)

        try:
            # Step 1: Fetch all users to find the one with matching email (phone)
            # Same approach as ChangeUserPasswordView
            users_url = f"{base_url}/users"
            response = requests.get(users_url, auth=auth)

            if response.status_code != 200:
                logger.error(f"Failed to fetch users from Traccar: {response.status_code} - {response.text}")
                # Return false by default so the flow can continue
                return Response({
                    "exists": False,
                    "error": "Unable to verify user existence at this time."
                }, status=200)

            users = response.json()

            # Step 2: Find user where email matches phone (same logic as ChangeUserPasswordView)
            target_user = None
            for user in users:
                if user.get('email') == phone:
                    target_user = user
                    break

            # Return whether user exists
            user_exists = target_user is not None
            
            return Response({"exists": user_exists}, status=200)

        except Exception as e:
            logger.error(f"CheckUserExistsView error: {str(e)}")
            # Return false by default so the flow can continue
            return Response({
                "exists": False,
                "error": "Unable to verify user existence."
            }, status=200)
            

class FetchPositionsTimeRangeView(APIView):
    #permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get the time range of the last 200 positions for a device.
        
        Query parameters:
        - deviceId (required): The device ID
        
        Returns:
        - from: datetime of the oldest position in the last 200
        - to: datetime of the newest position in the last 200
        - count: actual number of positions found
        """
        device_id = request.query_params.get('deviceId')
        
        if not device_id:
            return Response({"error": "Device ID is required"}, status=400)
        
        try:
            time_range = self._get_positions_time_range(device_id)
            return Response(time_range, status=200)
            
        except Exception as e:
            logger.error(f"Error in FetchPositionsTimeRangeView: {str(e)}")
            return Response({"error": f"An error occurred: {str(e)}"}, status=500)
    
    def _get_positions_time_range(self, device_id):
        """Get the time range of the last 200 positions for a device."""
        
        with connections['device_user_db'].cursor() as cursor:
            query = """
                SELECT MIN(fixtime) as min_time, MAX(fixtime) as max_time, COUNT(*) as total_count
                FROM (
                    SELECT fixtime 
                    FROM tc_positions 
                    WHERE deviceid = %s 
                    ORDER BY fixtime DESC 
                    LIMIT 200
                ) as last_positions
            """
            
            cursor.execute(query, [device_id])
            result = cursor.fetchone()
            
            if result and result[0] and result[1]:
                # Format dates to be compatible with Traccar API (remove microseconds)
                min_time = result[0].replace(microsecond=0).isoformat() + 'Z'
                max_time = result[1].replace(microsecond=0).isoformat() + 'Z'
                
                return {
                    'from': min_time,
                    'to': max_time,
                    'count': result[2]
                }
            else:
                return {
                    'from': None,
                    'to': None,
                    'count': 0
                }

from requests.auth import HTTPBasicAuth
import logging
from rest_framework.response import Response
from django.conf import settings
import requests

logger = logging.getLogger(__name__)

class TraccarDuplicateDeviceError(Exception):
    """Raised when Traccar reports duplicate device uniqueId."""
    pass


class TraccarDuplicateUserError(Exception):
    """Raised when Traccar reports duplicate user (email/phone/username)."""
    pass


class HandleUserDeviceLinkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Expected body:
        {
          "user": {
            "name": "...",
            "email": "...",
            "phone": "...",
            "password": "..."
          },
          "device": {
            "name": "...",
            "uniqueId": "...",
            "phone": "..."
          },
          "confirm": true/false   # optional
        }
        """
        data = request.data
        device_payload = data.get("device") or {}
        user_payload = data.get("user") or {}
        confirm = bool(data.get("confirm"))

        if not device_payload or not user_payload:
            return Response(
                {"error": "Both 'device' and 'user' data are required."},
                status=400
            )

        phone = user_payload.get("phone")
        unique_id = device_payload.get("uniqueId")

        if not phone:
            return Response({"error": "user.phone is required"}, status=400)
        if not unique_id:
            return Response({"error": "device.uniqueId is required"}, status=400)

        try:
            # 1) Find or create user (with confirmation step if already exists)
            user_obj = self._find_user_by_phone(phone)

            if user_obj and not confirm:
                # User exists, ask frontend to confirm before proceeding
                short_user = {
                    "id": user_obj.get("id"),
                    "name": user_obj.get("name"),
                    "email": user_obj.get("email"),
                    "phone": user_obj.get("phone"),
                }
                return Response(
                    {
                        "status": "user_exists",
                        "message": "User already exists in Traccar. Confirm to create and link device.",
                        "user": short_user,
                    },
                    status=200,
                )

            if not user_obj:
                # Create new user in Traccar
                user_obj = self._create_traccar_user(user_payload)

            # 2) Check if device already exists
            device_obj = self._find_device_by_unique_id(unique_id)
            if device_obj:
                # Device already exists – return clean message
                return Response(
                    {
                        "status": "device_exists",
                        "message": "دستگاه به این سریال در سامانه موجود است.",
                        "device": device_obj,
                    },
                    status=409,
                )

            device_payload["expirationTime"] = (
                datetime.utcnow() + timedelta(days=365)
            ).strftime("%Y-%m-%dT%H:%M:%S.000+00:00")
            
            # 3) Create device in Traccar
            try:
                device_obj = self._create_traccar_device(device_payload)
            except TraccarDuplicateDeviceError:
                # Race condition: device just created; fetch and report nicely
                existing = self._find_device_by_unique_id(unique_id)
                return Response(
                    {
                        "status": "device_exists",
                        "message": "Device with this uniqueId already exists in Traccar.",
                        "device": existing,
                    },
                    status=409,
                )

            # 4) Link user and device
            self._link_user_device(user_obj["id"], device_obj["id"])


            # 4b) Also link device to the reseller (current Django user)
            reseller_phone = getattr(request.user, "phone", None)
            if reseller_phone:
                reseller_user = self._find_user_by_phone(reseller_phone)
                if reseller_user:
                    try:
                        self._link_user_device(reseller_user["id"], device_obj["id"])
                    except Exception as e:
                        logger.warning(
                            "Failed to link device %s to reseller %s: %s",
                            device_obj.get("id"),
                            reseller_user.get("id"),
                            e,
                        )
                        
            return Response(
                {
                    "status": "ok",
                    "message": "User and device created and linked successfully.",
                    "user": user_obj,
                    "device": device_obj,
                },
                status=201,
            )

        except TraccarDuplicateUserError:
            return Response(
                {
                    "status": "user_duplicate",
                    "message": "User with these credentials already exists in Traccar.",
                },
                status=409,
            )
        except requests.RequestException as e:
            logger.exception("Traccar request error")
            return Response({"error": str(e)}, status=502)
        except Exception as e:
            logger.exception("HandleUserDeviceLinkView error")
            return Response({"error": str(e)}, status=500)

    # ---------- helpers ----------

    def _auth(self):
        return HTTPBasicAuth(
            settings.TRACCAR_API_USERNAME,
            settings.TRACCAR_API_PASSWORD
        )

    def _find_user_by_phone(self, phone: str):
        """
        Find Traccar user by phone (or email == phone).
        """
        url = f"{settings.TRACCAR_API_URL}/users"
        r = requests.get(url, auth=self._auth(), timeout=30)
        r.raise_for_status()

        data = r.json()
        if isinstance(data, dict):
            data = [data]

        for u in data:
            if u.get("phone") == phone or u.get("email") == phone:
                return u
        return None

    def _create_traccar_user(self, payload: dict):
        """
        Create user in Traccar, with duplicate detection.
        """
        url = f"{settings.TRACCAR_API_URL}/users"
        r = requests.post(url, json=payload, auth=self._auth(), timeout=30)

        if r.status_code == 200:
            return r.json()

        # Detect duplicate user errors by constraint name or generic duplicate message
        txt = r.text or ""
        if "duplicate key value" in txt or "tc_users_" in txt:
            logger.warning(f"Duplicate user in Traccar: {txt}")
            raise TraccarDuplicateUserError()

        logger.error(f"Failed to create user: {r.status_code} - {txt}")
        raise Exception(f"Failed to create user: {txt}")

    def _find_device_by_unique_id(self, unique_id: str):
        """
        Find Traccar device by uniqueId.
        """
        url = f"{settings.TRACCAR_API_URL}/devices"
        r = requests.get(
            url,
            params={"uniqueId": unique_id},
            auth=self._auth(),
            timeout=30,
        )
        r.raise_for_status()

        data = r.json()
        if isinstance(data, dict):
            data = [data]

        if data:
            return data[0]
        return None

    def _create_traccar_device(self, payload: dict):
        """
        Create device in Traccar, with duplicate uniqueId detection.
        """
        url = f"{settings.TRACCAR_API_URL}/devices"
        r = requests.post(url, json=payload, auth=self._auth(), timeout=30)

        if r.status_code == 200:
            return r.json()

        txt = r.text or ""
        # Detect duplicate uniqueId error from Traccar / Postgres
        if (
            "tc_devices_uniqueid_key" in txt
            or ("duplicate key value" in txt and "uniqueid" in txt.lower())
        ):
            logger.warning(f"Duplicate device uniqueId in Traccar: {txt}")
            raise TraccarDuplicateDeviceError()

        logger.error(f"Failed to create device: {r.status_code} - {txt}")
        raise Exception(f"Failed to create device: {txt}")

    def _link_user_device(self, user_id: int, device_id: int):
        """
        Link user and device in Traccar. Treat 200/201/204 as success.
        """
        url = f"{settings.TRACCAR_API_URL}/permissions"
        payload = {"userId": user_id, "deviceId": device_id}
        r = requests.post(url, json=payload, auth=self._auth(), timeout=30)

        # Traccar often returns 204 No Content for successful permission changes
        if r.status_code in (200, 201, 204):
            return

        logger.error(
            "Failed to link user to device: %s - %s",
            r.status_code,
            r.text,
        )
        raise Exception(f"Failed to link user and device: {r.text}")