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
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = ExpiredDevicesPagination

    def get(self, request, *args, **kwargs):
        # Get the current time
        current_time = timezone.now()

        # Search filter parameter
        search_term = request.query_params.get('search', '').strip()

        # Use 'uzradyab' connection for read-only access, ordered by expirationtime (newest first)
        with connections['uzradyab'].cursor() as cursor:
            query = """
                SELECT id, name, uniqueid, phone, expirationtime
                FROM tc_devices
                WHERE expirationtime IS NOT NULL
                AND expirationtime < %s
            """
            params = [current_time]

            # Apply search filtering
            if search_term:
                query += " AND (name ILIKE %s OR uniqueid ILIKE %s OR phone ILIKE %s)"
                params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])

            query += " ORDER BY expirationtime DESC"
            cursor.execute(query, params)

            # Fetch all results
            expired_devices = cursor.fetchall()

        # Convert data to a list of dictionaries
        devices_list = [
            {
                "id": device[0],
                "name": device[1],
                "uniqueid": device[2],
                "phone": device[3],
                "expirationtime": device[4],
            }
            for device in expired_devices
        ]

        # Paginate the response
        paginator = ExpiredDevicesPagination()
        paginated_devices = paginator.paginate_queryset(devices_list, request, view=self)
        return paginator.get_paginated_response(paginated_devices)
