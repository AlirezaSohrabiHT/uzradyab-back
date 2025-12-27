# traccar_calls/admin_urls.py - Admin URLs for device and user management

from django.urls import path
from .admin_views import (
    AdminDeviceListView,
    AdminUserListView,
    AdminUpdateDeviceExpirationView,
    AdminDeviceUsersView,
    AdminDashboardStatsView,
    AdminBulkExtendExpirationView,
    AdminUpdateTraccarUserView,
    AdminSendSMSView,
)

urlpatterns = [
    # Dashboard stats
    path('stats/', AdminDashboardStatsView.as_view(), name='admin_stats'),
    
    # Device management
    # path('devices/', AdminDeviceListView.as_view(), name='admin_devices'),
    path('devices/<int:device_id>/users/', AdminDeviceUsersView.as_view(), name='admin_device_users'),
    path('devices/<int:device_id>/expiration/', AdminUpdateDeviceExpirationView.as_view(), name='admin_device_expiration'),
    path('devices/bulk-extend/', AdminBulkExtendExpirationView.as_view(), name='admin_bulk_extend'),
    
    # User management
    path('users/', AdminUserListView.as_view(), name='admin_users'),
    path('users/<int:user_id>/', AdminUpdateTraccarUserView.as_view(), name='admin_update_user'),
    
    # SMS
    path('send-sms/', AdminSendSMSView.as_view(), name='admin_send_sms'),
]