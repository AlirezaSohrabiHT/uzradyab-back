"""
URL configuration for managerPanel project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from main.views import PayAPIView,  VerifyAPIView , AccountChargeAPIView , SendRequestAPIView,\
      PaymentListView, ResellerPaymentListView, buy_package
from django.urls import path , include
from main.views import PayAPIView, VerifyAPIView, AccountChargeAPIView, SendRequestAPIView, ResellersListView
from uzradyabHandler.views import ExpiredDevicesView 
from health.views import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('pay/', PayAPIView.as_view(), name='pay'),
    path('request/', SendRequestAPIView.as_view(), name='request'),
    path('accountChargeList/', AccountChargeAPIView.as_view(), name='account_charge'),
    path('verify/', VerifyAPIView.as_view(), name='verify'),
    path('payments/', PaymentListView.as_view(), name='payment-list'),
    path('reseller-payments/', ResellerPaymentListView.as_view(), name='ResellerPaymentListView-list'),
    path('resellers/', ResellersListView.as_view(), name='ResellersListView-list'),
    path('buy-package/', buy_package, name='buy_package'),
    path('api/traccar/', include('traccar_calls.urls')),
    path('api/services/', include('services.urls')),
    path('api/main/', include('main.urls')),
    path('api/accounts/', include('accounts.urls')),
    path('deviceExpired/', ExpiredDevicesView.as_view(), name='device_expired'),
    path('deviceExpired/<int:pk>/', ExpiredDevicesView.as_view(), name='expired-device-detail'),
    path("otp/", include("otpmanager.urls")),  # Change "otp_app" to your actual app name
    path('health/', health_check, name='health_check'),

]
