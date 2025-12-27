# traccar_calls/admin_views.py - Admin views for device and user management

import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.db import connections
from django.utils import timezone
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
import logging

logger = logging.getLogger('main')


# Permission classes
class IsAdminUser(BasePermission):
    """Permission class to check if user is admin"""
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (
                getattr(request.user, 'user_type', None) == 'admin' or
                request.user.is_superuser
            )
        )


class IsSupportOrAdmin(BasePermission):
    """Permission class to check if user is support or admin"""
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (
                getattr(request.user, 'user_type', None) in ['support', 'admin'] or
                request.user.is_superuser or
                request.user.is_staff
            )
        )


class AdminDevicePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdminDeviceListView(APIView):
    """
    Admin view to list all devices with their users from Traccar database
    """
    permission_classes = [IsAuthenticated, IsSupportOrAdmin]
    pagination_class = AdminDevicePagination

    def get(self, request):
        try:
            search = request.query_params.get('search', '').strip()
            status_filter = request.query_params.get('status', '')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            offset = (page - 1) * page_size
            
            device_db = connections['device_user_db']
            
            base_query = """
                SELECT 
                    d.id as device_id,
                    d.name as device_name,
                    d.uniqueid as device_uniqueid,
                    d.phone as device_phone,
                    d.status as device_status,
                    d.disabled as device_disabled,
                    d.expirationtime,
                    d.lastupdate,
                    u.id as user_id,
                    u.name as user_name,
                    u.email as user_email,
                    u.phone as user_phone,
                    u.administrator as user_is_admin
                FROM tc_devices d
                LEFT JOIN tc_user_device ud ON d.id = ud.deviceid
                LEFT JOIN tc_users u ON ud.userid = u.id AND u.administrator = false
                WHERE 1=1
            """
            
            params = []
            
            if search:
                base_query += """
                    AND (
                        LOWER(d.name) LIKE LOWER(%s) OR
                        LOWER(d.uniqueid) LIKE LOWER(%s) OR
                        LOWER(d.phone) LIKE LOWER(%s) OR
                        LOWER(u.name) LIKE LOWER(%s) OR
                        LOWER(u.phone) LIKE LOWER(%s) OR
                        LOWER(u.email) LIKE LOWER(%s)
                    )
                """
                search_pattern = f'%{search}%'
                params.extend([search_pattern] * 6)
            
            current_time = timezone.now()
            if status_filter == 'expired':
                base_query += " AND d.expirationtime IS NOT NULL AND d.expirationtime < %s"
                params.append(current_time)
            elif status_filter == 'active':
                base_query += " AND (d.expirationtime IS NULL OR d.expirationtime >= %s)"
                params.append(current_time)
            elif status_filter == 'online':
                base_query += " AND d.status = 'online'"
            elif status_filter == 'offline':
                base_query += " AND d.status = 'offline'"
            elif status_filter == 'disabled':
                base_query += " AND d.disabled = true"
            
            with device_db.cursor() as cursor:
                cursor.execute(f"""
                    SELECT COUNT(DISTINCT d.id) 
                    FROM tc_devices d
                    LEFT JOIN tc_user_device ud ON d.id = ud.deviceid
                    LEFT JOIN tc_users u ON ud.userid = u.id AND u.administrator = false
                    WHERE 1=1
                    {base_query.split('WHERE 1=1')[1].split('ORDER BY')[0] if 'ORDER BY' in base_query else base_query.split('WHERE 1=1')[1]}
                """, params)
                total_count = cursor.fetchone()[0]
            
            final_query = base_query + """
                ORDER BY d.expirationtime ASC NULLS LAST, d.id DESC
                LIMIT %s OFFSET %s
            """
            params.extend([page_size, offset])
            
            with device_db.cursor() as cursor:
                cursor.execute(final_query, params)
                rows = cursor.fetchall()
            
            devices_dict = {}
            for row in rows:
                device_id = row[0]
                
                if device_id not in devices_dict:
                    expiration_time = row[6]
                    is_expired = False
                    if expiration_time:
                        if expiration_time.tzinfo is None:
                            expiration_time = timezone.make_aware(expiration_time)
                        is_expired = expiration_time < current_time
                    
                    devices_dict[device_id] = {
                        'id': device_id,
                        'name': row[1] or '',
                        'uniqueId': row[2] or '',
                        'phone': row[3] or '',
                        'status': row[4] or 'unknown',
                        'disabled': row[5] or False,
                        'expirationTime': row[6].isoformat() if row[6] else None,
                        'lastUpdate': row[7].isoformat() if row[7] else None,
                        'isExpired': is_expired,
                        'users': []
                    }
                
                if row[8] and not row[12]:
                    user_info = {
                        'id': row[8],
                        'name': row[9] or '',
                        'email': row[10] or '',
                        'phone': row[11] or '',
                    }
                    if user_info not in devices_dict[device_id]['users']:
                        devices_dict[device_id]['users'].append(user_info)
            
            devices_list = list(devices_dict.values())
            total_pages = (total_count + page_size - 1) // page_size
            
            return Response({
                'count': total_count,
                'total_pages': total_pages,
                'current_page': page,
                'page_size': page_size,
                'next': page < total_pages,
                'previous': page > 1,
                'results': devices_list
            }, status=200)
            
        except Exception as e:
            logger.exception("Error in AdminDeviceListView")
            return Response({
                'error': str(e),
                'message': 'خطا در دریافت لیست دستگاه‌ها'
            }, status=500)


class AdminUserListView(APIView):
    """Admin view to list all users from Traccar database"""
    permission_classes = [IsAuthenticated, IsSupportOrAdmin]

    def get(self, request):
        try:
            search = request.query_params.get('search', '').strip()
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            offset = (page - 1) * page_size
            
            device_db = connections['device_user_db']
            
            base_query = """
                SELECT 
                    u.id,
                    u.name,
                    u.email,
                    u.phone,
                    u.administrator,
                    u.disabled,
                    u.expirationtime,
                    COUNT(DISTINCT ud.deviceid) as device_count
                FROM tc_users u
                LEFT JOIN tc_user_device ud ON u.id = ud.userid
                WHERE u.administrator = false
            """
            
            params = []
            
            if search:
                base_query += """
                    AND (
                        LOWER(u.name) LIKE LOWER(%s) OR
                        LOWER(u.email) LIKE LOWER(%s) OR
                        LOWER(u.phone) LIKE LOWER(%s)
                    )
                """
                search_pattern = f'%{search}%'
                params.extend([search_pattern] * 3)
            
            base_query += " GROUP BY u.id"
            
            with device_db.cursor() as cursor:
                count_params = params.copy()
                cursor.execute(f"SELECT COUNT(*) FROM ({base_query}) as subquery", count_params)
                total_count = cursor.fetchone()[0]
            
            final_query = base_query + " ORDER BY u.id DESC LIMIT %s OFFSET %s"
            params.extend([page_size, offset])
            
            with device_db.cursor() as cursor:
                cursor.execute(final_query, params)
                rows = cursor.fetchall()
            
            users = []
            for row in rows:
                users.append({
                    'id': row[0],
                    'name': row[1] or '',
                    'email': row[2] or '',
                    'phone': row[3] or '',
                    'administrator': row[4] or False,
                    'disabled': row[5] or False,
                    'expirationTime': row[6].isoformat() if row[6] else None,
                    'deviceCount': row[7]
                })
            
            total_pages = (total_count + page_size - 1) // page_size
            
            return Response({
                'count': total_count,
                'total_pages': total_pages,
                'current_page': page,
                'page_size': page_size,
                'next': page < total_pages,
                'previous': page > 1,
                'results': users
            }, status=200)
            
        except Exception as e:
            logger.exception("Error in AdminUserListView")
            return Response({
                'error': str(e),
                'message': 'خطا در دریافت لیست کاربران'
            }, status=500)


class AdminUpdateDeviceExpirationView(APIView):
    """Admin view to update device expiration date"""
    permission_classes = [IsAuthenticated, IsSupportOrAdmin]

    def put(self, request, device_id):
        try:
            new_expiration = request.data.get('expirationTime')
            extend_days = request.data.get('extendDays')
            
            if not new_expiration and not extend_days:
                return Response({
                    'error': 'لطفاً تاریخ انقضا یا تعداد روز تمدید را وارد کنید'
                }, status=400)
            
            url = f"{settings.TRACCAR_API_URL}/devices/{device_id}"
            auth = HTTPBasicAuth(settings.TRACCAR_API_USERNAME, settings.TRACCAR_API_PASSWORD)
            
            response = requests.get(url, auth=auth, timeout=30)
            
            if response.status_code != 200:
                return Response({
                    'error': 'دستگاه یافت نشد',
                    'details': response.text
                }, status=response.status_code)
            
            device = response.json()
            
            if extend_days:
                current_exp = device.get('expirationTime')
                if current_exp:
                    try:
                        current_exp_dt = datetime.fromisoformat(current_exp.replace('Z', '+00:00'))
                        if current_exp_dt < timezone.now():
                            base_time = timezone.now()
                        else:
                            base_time = current_exp_dt
                    except:
                        base_time = timezone.now()
                else:
                    base_time = timezone.now()
                
                new_exp_dt = base_time + timedelta(days=int(extend_days))
                new_expiration = new_exp_dt.strftime('%Y-%m-%dT%H:%M:%S.000+00:00')
            
            device['expirationTime'] = new_expiration
            
            update_response = requests.put(url, json=device, auth=auth, timeout=30)
            
            if update_response.status_code == 200:
                return Response({
                    'success': True,
                    'message': 'تاریخ انقضا با موفقیت به‌روزرسانی شد',
                    'device': update_response.json()
                }, status=200)
            else:
                return Response({
                    'error': 'خطا در به‌روزرسانی دستگاه',
                    'details': update_response.text
                }, status=update_response.status_code)
                
        except Exception as e:
            logger.exception("Error in AdminUpdateDeviceExpirationView")
            return Response({
                'error': str(e),
                'message': 'خطا در به‌روزرسانی تاریخ انقضا'
            }, status=500)


class AdminDeviceUsersView(APIView):
    """Get all users linked to a specific device"""
    permission_classes = [IsAuthenticated, IsSupportOrAdmin]

    def get(self, request, device_id):
        try:
            device_db = connections['device_user_db']
            
            query = """
                SELECT 
                    u.id,
                    u.name,
                    u.email,
                    u.phone,
                    u.administrator,
                    u.disabled
                FROM tc_users u
                JOIN tc_user_device ud ON u.id = ud.userid
                WHERE ud.deviceid = %s
                ORDER BY u.administrator DESC, u.name ASC
            """
            
            with device_db.cursor() as cursor:
                cursor.execute(query, [device_id])
                rows = cursor.fetchall()
            
            users = []
            for row in rows:
                users.append({
                    'id': row[0],
                    'name': row[1] or '',
                    'email': row[2] or '',
                    'phone': row[3] or '',
                    'administrator': row[4] or False,
                    'disabled': row[5] or False,
                })
            
            return Response(users, status=200)
            
        except Exception as e:
            logger.exception("Error in AdminDeviceUsersView")
            return Response({
                'error': str(e),
                'message': 'خطا در دریافت کاربران دستگاه'
            }, status=500)


class AdminUpdateTraccarUserView(APIView):
    """Update Traccar user email (phone) and password"""
    permission_classes = [IsAuthenticated, IsSupportOrAdmin]

    def put(self, request, user_id):
        try:
            new_email = request.data.get('email')  # email is used as phone
            new_password = request.data.get('password')
            new_name = request.data.get('name')
            
            if not new_email and not new_password and not new_name:
                return Response({
                    'error': 'لطفاً حداقل یک فیلد برای به‌روزرسانی وارد کنید'
                }, status=400)
            
            # Get current user data from Traccar API
            url = f"{settings.TRACCAR_API_URL}/users/{user_id}"
            auth = HTTPBasicAuth(settings.TRACCAR_API_USERNAME, settings.TRACCAR_API_PASSWORD)
            
            response = requests.get(url, auth=auth, timeout=30)
            
            if response.status_code != 200:
                return Response({
                    'error': 'کاربر یافت نشد',
                    'details': response.text
                }, status=response.status_code)
            
            user = response.json()
            
            # Update fields
            if new_email:
                user['email'] = new_email
                user['phone'] = new_email  # Keep phone synced with email
            
            if new_name:
                user['name'] = new_name
            
            if new_password:
                user['password'] = new_password
            
            # Update user in Traccar
            update_response = requests.put(url, json=user, auth=auth, timeout=30)
            
            if update_response.status_code == 200:
                updated_user = update_response.json()
                return Response({
                    'success': True,
                    'message': 'اطلاعات کاربر با موفقیت به‌روزرسانی شد',
                    'user': {
                        'id': updated_user.get('id'),
                        'name': updated_user.get('name'),
                        'email': updated_user.get('email'),
                        'phone': updated_user.get('phone'),
                    }
                }, status=200)
            else:
                return Response({
                    'error': 'خطا در به‌روزرسانی کاربر',
                    'details': update_response.text
                }, status=update_response.status_code)
                
        except Exception as e:
            logger.exception("Error in AdminUpdateTraccarUserView")
            return Response({
                'error': str(e),
                'message': 'خطا در به‌روزرسانی کاربر'
            }, status=500)


class AdminSendSMSView(APIView):
    """Send SMS via Kavenegar with pattern uzradyabexpire"""
    permission_classes = [IsAuthenticated, IsSupportOrAdmin]

    def post(self, request):
        try:
            from kavenegar import KavenegarAPI, APIException, HTTPException
            
            phone = request.data.get('phone')
            device_name = request.data.get('deviceName', '')
            
            if not phone:
                return Response({
                    'error': 'شماره تلفن الزامی است'
                }, status=400)
            
            # Normalize phone number for Kavenegar
            phone = str(phone).strip()
            
            # Remove any non-digit characters
            phone = ''.join(filter(str.isdigit, phone))
            
            # Convert to proper format (09xxxxxxxxx)
            if phone.startswith('98') and len(phone) == 12:
                # 989123456789 -> 09123456789
                phone = '0' + phone[2:]
            elif phone.startswith('9') and len(phone) == 10:
                # 9123456789 -> 09123456789
                phone = '0' + phone
            elif not phone.startswith('0') and len(phone) == 10:
                # 9123456789 -> 09123456789
                phone = '0' + phone
            
            # Validate phone number format
            if not (phone.startswith('09') and len(phone) == 11):
                return Response({
                    'error': f'فرمت شماره تلفن نادرست است: {phone}',
                    'message': 'شماره تلفن باید با 09 شروع شود و 11 رقم باشد'
                }, status=400)
            
            # Initialize Kavenegar API
            api = KavenegarAPI('415270574F5349545265306244503252575A44584C52614C69736C6C56437841')
            device = (device_name or 'دستگاه').replace(' ', '_')
            params = {
                'receptor': phone,
                'template': 'uzradyabexpire',
                'token': f"{device}",
                'type': 'sms',
            }
            
            response = api.verify_lookup(params)
            
            logger.info(f"SMS sent successfully to {phone} for device {device_name}")
            
            return Response({
                'success': True,
                'message': 'پیامک با موفقیت ارسال شد',
                'response': response
            }, status=200)
                
        except APIException as e:
            logger.error(f"Kavenegar API error: {e}")
            return Response({
                'error': f'خطا در API کاوه‌نگار: {str(e)}',
                'message': 'خطا در ارسال پیامک'
            }, status=400)
        except HTTPException as e:
            logger.error(f"Kavenegar HTTP error: {e}")
            return Response({
                'error': f'خطا در اتصال به کاوه‌نگار: {str(e)}',
                'message': 'خطا در ارسال پیامک'
            }, status=500)
        except Exception as e:
            logger.exception("Error in AdminSendSMSView")
            return Response({
                'error': str(e),
                'message': 'خطا در ارسال پیامک'
            }, status=500)



class AdminDashboardStatsView(APIView):
    """Get dashboard statistics for admin"""
    permission_classes = [IsAuthenticated, IsSupportOrAdmin]

    def get(self, request):
        try:
            device_db = connections['device_user_db']
            current_time = timezone.now()
            
            with device_db.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM tc_devices")
                total_devices = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM tc_devices WHERE status = 'online'")
                online_devices = cursor.fetchone()[0]
                
                cursor.execute(
                    "SELECT COUNT(*) FROM tc_devices WHERE expirationtime IS NOT NULL AND expirationtime < %s",
                    [current_time]
                )
                expired_devices = cursor.fetchone()[0]
                
                seven_days_later = current_time + timedelta(days=7)
                cursor.execute(
                    """SELECT COUNT(*) FROM tc_devices 
                       WHERE expirationtime IS NOT NULL 
                       AND expirationtime >= %s 
                       AND expirationtime <= %s""",
                    [current_time, seven_days_later]
                )
                expiring_soon = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM tc_users WHERE administrator = false")
                total_users = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM tc_devices WHERE disabled = true")
                disabled_devices = cursor.fetchone()[0]
            
            return Response({
                'totalDevices': total_devices,
                'onlineDevices': online_devices,
                'offlineDevices': total_devices - online_devices,
                'expiredDevices': expired_devices,
                'expiringSoon': expiring_soon,
                'totalUsers': total_users,
                'disabledDevices': disabled_devices,
            }, status=200)
            
        except Exception as e:
            logger.exception("Error in AdminDashboardStatsView")
            return Response({
                'error': str(e),
                'message': 'خطا در دریافت آمار'
            }, status=500)


class AdminBulkExtendExpirationView(APIView):
    """Bulk extend expiration for multiple devices"""
    permission_classes = [IsAuthenticated, IsSupportOrAdmin]

    def post(self, request):
        try:
            device_ids = request.data.get('deviceIds', [])
            extend_days = request.data.get('extendDays')
            
            if not device_ids or not extend_days:
                return Response({
                    'error': 'لطفاً دستگاه‌ها و تعداد روز را مشخص کنید'
                }, status=400)
            
            auth = HTTPBasicAuth(settings.TRACCAR_API_USERNAME, settings.TRACCAR_API_PASSWORD)
            
            success_count = 0
            failed_count = 0
            errors = []
            
            for device_id in device_ids:
                try:
                    url = f"{settings.TRACCAR_API_URL}/devices/{device_id}"
                    response = requests.get(url, auth=auth, timeout=30)
                    
                    if response.status_code != 200:
                        failed_count += 1
                        errors.append(f"Device {device_id}: Not found")
                        continue
                    
                    device = response.json()
                    
                    current_exp = device.get('expirationTime')
                    if current_exp:
                        try:
                            current_exp_dt = datetime.fromisoformat(current_exp.replace('Z', '+00:00'))
                            if current_exp_dt < timezone.now():
                                base_time = timezone.now()
                            else:
                                base_time = current_exp_dt
                        except:
                            base_time = timezone.now()
                    else:
                        base_time = timezone.now()
                    
                    new_exp_dt = base_time + timedelta(days=int(extend_days))
                    device['expirationTime'] = new_exp_dt.strftime('%Y-%m-%dT%H:%M:%S.000+00:00')
                    
                    update_response = requests.put(url, json=device, auth=auth, timeout=30)
                    
                    if update_response.status_code == 200:
                        success_count += 1
                    else:
                        failed_count += 1
                        errors.append(f"Device {device_id}: Update failed")
                        
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Device {device_id}: {str(e)}")
            
            return Response({
                'success': True,
                'message': f'{success_count} دستگاه با موفقیت تمدید شد',
                'successCount': success_count,
                'failedCount': failed_count,
                'errors': errors if errors else None
            }, status=200)
            
        except Exception as e:
            logger.exception("Error in AdminBulkExtendExpirationView")
            return Response({
                'error': str(e),
                'message': 'خطا در تمدید گروهی'
            }, status=500)