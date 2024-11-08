# views.py
from django.db import connections
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

class ExpiredDevicesPagination(PageNumberPagination):
    page_size = 10  # Default items per page
    page_size_query_param = 'pageSize'
    max_page_size = 100

class ExpiredDevicesView(APIView):
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]
    pagination_class = ExpiredDevicesPagination

    def get(self, request, *args, **kwargs):
        # Get the current time
        current_time = timezone.now()

        # Search filter parameter
        search_term = request.query_params.get('search', '').strip()

        # Use 'uzradyab' connection for read-only access, ordered by expirationtime (newest first)
        with connections['uzradyab'].cursor() as cursor:
            query = """
                SELECT 
                    d.id, d.name, d.uniqueid, d.phone, d.expirationtime,
                    u.email, u.phone as user_phone
                FROM 
                    tc_devices d
                JOIN 
                    tc_user_device ud ON d.id = ud.deviceid
                JOIN 
                    tc_users u ON ud.userid = u.id
                WHERE 
                    d.expirationtime IS NOT NULL
                    AND d.expirationtime < %s
            """
            params = [current_time]

            # Apply search filtering
            if search_term:
                query += " AND (d.name ILIKE %s OR d.uniqueid ILIKE %s OR d.phone ILIKE %s)"
                params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])

            query += " ORDER BY d.expirationtime DESC"
            cursor.execute(query, params)

            # Fetch all results
            expired_devices = cursor.fetchall()

        # Group devices and users
        devices_dict = {}
        for device in expired_devices:
            device_id = device[0]
            if device_id not in devices_dict:
                devices_dict[device_id] = {
                    "id": device[0],
                    "name": device[1],
                    "uniqueid": device[2],
                    "phone": device[3],
                    "expirationtime": device[4],
                    "user_emails": [],
                    "user_phones": [],
                }
            # Add user details
            devices_dict[device_id]["user_emails"].append(device[5])
            devices_dict[device_id]["user_phones"].append(device[6])

        # Convert the grouped data to a list
        devices_list = list(devices_dict.values())

        # Paginate the response
        paginator = ExpiredDevicesPagination()
        paginated_devices = paginator.paginate_queryset(devices_list, request, view=self)
        return paginator.get_paginated_response(paginated_devices)
