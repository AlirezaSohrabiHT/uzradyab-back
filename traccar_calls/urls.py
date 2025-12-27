from django.urls import path, include
from .views import (
    HandleUserDeviceLinkView, CheckUserExistsView, FetchPositionsTimeRangeView,
    ChangeUserPasswordView, LinkUserToDeviceView, CreateTraccarDeviceView,
    CreateTraccarUserView, UpdateTraccarUserView, UpdateDeviceView,
    TraccarSessionView, DeviceUsersView, FetchStatisticsView, FetchDriversView,
    FetchDevicesView, FetchUsersView
)
from .admin_views import (
    AdminDeviceListView, AdminUserListView, AdminUpdateDeviceExpirationView,
    AdminDeviceUsersView, AdminDashboardStatsView, AdminBulkExtendExpirationView   ,  AdminUpdateTraccarUserView,
    AdminSendSMSView,
)

urlpatterns = [
    # Existing URLs
    path('session/', TraccarSessionView.as_view(), name='traccar-session'),
    path('devices/', FetchDevicesView.as_view(), name='traccar-devices'),
    path('drivers/', FetchDriversView.as_view(), name='traccar-drivers'),
    path('users/', FetchUsersView.as_view(), name='traccar_users'),
    path('statistics/', FetchStatisticsView.as_view(), name='traccar_statistics'),
    path('device-users/', DeviceUsersView.as_view(), name='traccar_device_users'),
    path('devices/<int:device_id>/', UpdateDeviceView.as_view(), name='device-update'),
    path('users/<int:user_id>/', UpdateTraccarUserView.as_view(), name='user-update'),
    path('users/create/', CreateTraccarUserView.as_view(), name='traccar-user-create'),
    path('devices/create/', CreateTraccarDeviceView.as_view(), name='traccar-device-create'),
    path('link-user-device/', LinkUserToDeviceView.as_view(), name='traccar-device-create'),
    path('change-password/', ChangeUserPasswordView.as_view(), name='change-password'),
    path('check-user-exists/', CheckUserExistsView.as_view(), name='change-user-exist'),
    path('positions/time-range/', FetchPositionsTimeRangeView.as_view(), name='positions-time-range'),
    path('handle-user-device/', HandleUserDeviceLinkView.as_view(), name='handle-user-device'),
    
    # Admin URLs - NEW
    path('admin/stats/', AdminDashboardStatsView.as_view(), name='admin_stats'),
    path('admin/devices/', AdminDeviceListView.as_view(), name='admin_devices'),
    path('admin/devices/<int:device_id>/users/', AdminDeviceUsersView.as_view(), name='admin_device_users'),
    path('admin/devices/<int:device_id>/expiration/', AdminUpdateDeviceExpirationView.as_view(), name='admin_device_expiration'),
    path('admin/devices/bulk-extend/', AdminBulkExtendExpirationView.as_view(), name='admin_bulk_extend'),
    path('admin/users/', AdminUserListView.as_view(), name='admin_users'),
    path('admin/users/<int:user_id>/update/', AdminUpdateTraccarUserView.as_view(), name='admin_update_user'),
    path('admin/send-sms/', AdminSendSMSView.as_view(), name='admin_send_sms'),
]