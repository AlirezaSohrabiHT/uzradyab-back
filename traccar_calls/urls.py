from django.urls import path
from .views import TraccarSessionView ,DeviceUsersView , FetchStatisticsView, FetchDriversView, FetchDevicesView , FetchUsersView

urlpatterns = [
    path('session/', TraccarSessionView.as_view(), name='traccar-session'),
    path('devices/', FetchDevicesView.as_view(), name='traccar-devices'),
    path('drivers/', FetchDriversView.as_view(), name='traccar-drivers'),
    path('users/', FetchUsersView.as_view(), name='traccar_users'),
    path('statistics/', FetchStatisticsView.as_view(), name='traccar_statistics'),
    path('device-users/', DeviceUsersView.as_view(), name='traccar_device_users'),

]
