from django.urls import path
from .views import LoginView , CheckTraccarTokenView , GenerateTraccarTokenView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('check-traccar-token/', CheckTraccarTokenView.as_view(), name='check_traccar_token'),
    path('generate-traccar-token/', GenerateTraccarTokenView.as_view(), name='generate_traccar_token'),
]
