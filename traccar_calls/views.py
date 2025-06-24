import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
import requests
import logging
from django.db import connections
from django.conf import settings
from rest_framework.pagination import PageNumberPagination
from rest_framework import generics
logger = logging.getLogger(__name__)

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