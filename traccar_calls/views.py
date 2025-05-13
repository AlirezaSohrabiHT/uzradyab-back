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

class FetchDevicesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        base_url = settings.TRACCAR_API_URL
        url = f"{base_url}/devices"

        # Pass optional filters
        params = {
            key: request.query_params.getlist(key)
            for key in ["id", "uniqueId", "userId"]
            if request.query_params.get(key)
        }

        # Handle boolean `all` param
        if "all" in request.query_params:
            params["all"] = request.query_params.get("all")

        try:
            # Use HTTP Basic Auth with phone and raw_password
            response = requests.get(url, params=params, auth=(user.phone, user.raw_password))
            
            if response.status_code == 200:
                return Response(response.json(), status=200)
            else:
                return Response({
                    "error": "Failed to fetch devices from Traccar.",
                    "status_code": response.status_code,
                    "details": response.text,
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
                # For list parameters like deviceId, we might have multiple values
                if param in ["deviceId", "groupId"]:
                    values = request.query_params.getlist(param)
                    if values:
                        params[param] = values
                # For boolean parameters
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

        try:
            # Use HTTP Basic Auth with phone and raw_password
            response = requests.get(
                url, 
                params=params, 
                auth=(user.phone, user.raw_password)
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

class FetchUsersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        base_url = settings.TRACCAR_API_URL
        url = f"{base_url}/users"

        # Get query params
        params = {}
        
        # Handle userId query parameter (only for admin/manager users)
        if 'userId' in request.query_params:
            params['userId'] = request.query_params.get('userId')

        try:
            # Use HTTP Basic Auth with phone and raw_password
            response = requests.get(
                url, 
                params=params, 
                auth=(user.phone, user.raw_password)
            )
            
            if response.status_code == 200:
                return Response(response.json(), status=200)
            else:
                return Response({
                    "error": "Failed to fetch users from Traccar.",
                    "status_code": response.status_code,
                    "details": response.text,
                }, status=response.status_code)
        except Exception as e:
            return Response({
                "error": f"An error occurred while fetching users: {str(e)}",
                "status_code": 500
            }, status=500)
            
class FetchStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        base_url = settings.TRACCAR_API_URL
        url = f"{base_url}/statistics"

        # Get date range from query params or use default (last 7 days)
        try:
            from_date = request.query_params.get('from')
            if not from_date:
                # Default to 7 days ago
                from_date = (datetime.now() - timedelta(days=7)).isoformat() + 'Z'
            
            to_date = request.query_params.get('to')
            if not to_date:
                # Default to now
                to_date = datetime.now().isoformat() + 'Z'
            
            # Prepare query parameters
            params = {
                'from': from_date,
                'to': to_date
            }

            # Use HTTP Basic Auth with phone and raw_password
            response = requests.get(
                url, 
                params=params, 
                auth=(user.phone, user.raw_password)
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
        """Fetch user details from Traccar API for a specific user ID."""
        user = self.request.user
        base_url = settings.TRACCAR_API_URL
        
        try:
            # Fetch user details from Traccar API
            url = f"{base_url}/users/{user_id}"
            
            response = requests.get(
                url,
                auth=(user.phone, user.raw_password)
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch user {user_id}: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {str(e)}")
            return None