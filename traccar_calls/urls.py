from django.urls import path
from .views import LinkUserToDeviceView , CreateTraccarDeviceView , CreateTraccarUserView , UpdateTraccarUserView , UpdateDeviceView , TraccarSessionView ,DeviceUsersView , FetchStatisticsView, FetchDriversView, FetchDevicesView , FetchUsersView

urlpatterns = [
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

]
