from django.urls import path
from .views import LoginView , CheckTraccarTokenView , GenerateTraccarTokenView,\
    user_info, edit_profile, change_password, reset_password, user_balance

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('check-traccar-token/', CheckTraccarTokenView.as_view(), name='check_traccar_token'),
    path('generate-traccar-token/', GenerateTraccarTokenView.as_view(), name='generate_traccar_token'),
    path('info/', user_info, name='user_info'),
    path('balance/', user_balance, name='user_balance'),
    path('edit-profile/', edit_profile, name='edit_profile'),
    path('change-password/', change_password, name='change_password'),
    path('reset-password/', reset_password, name='reset_password'),
]
