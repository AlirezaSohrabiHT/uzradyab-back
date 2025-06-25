# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # For DRF option
    path('payments/', views.PaymentListView.as_view(), name='payment-list'),
    
    # For simple view option
    # path('api/payments/', views.payment_list_view, name='payment-list'),
]