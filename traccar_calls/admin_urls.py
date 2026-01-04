# traccar_calls/admin_urls.py

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
    AdminDeviceFollowUpView,
    AdminDeviceCallLogView,
    AdminDeviceCallHistoryView,
)

urlpatterns = [
    # Dashboard stats
    path('stats/', AdminDashboardStatsView.as_view(), name='admin_stats'),

    # Device management
    path('devices/', AdminDeviceListView.as_view(), name='admin_devices'),
    path('devices/<int:device_id>/users/', AdminDeviceUsersView.as_view(), name='admin_device_users'),
    path('devices/<int:device_id>/expiration/', AdminUpdateDeviceExpirationView.as_view(), name='admin_device_expiration'),
    path('devices/bulk-extend/', AdminBulkExtendExpirationView.as_view(), name='admin_bulk_extend'),

    # Follow-up + call
    path('devices/<int:device_id>/followup/', AdminDeviceFollowUpView.as_view(), name='admin_device_followup'),
    path('devices/<int:device_id>/call-log/', AdminDeviceCallLogView.as_view(), name='admin_device_call_log'),
    path('devices/<int:device_id>/call-history/', AdminDeviceCallHistoryView.as_view(), name='admin_device_call_history'),

    # User management
    path('users/', AdminUserListView.as_view(), name='admin_users'),
    path('users/<int:user_id>/update/', AdminUpdateTraccarUserView.as_view(), name='admin_update_user'),

    # SMS
    path('send-sms/', AdminSendSMSView.as_view(), name='admin_send_sms'),
]
