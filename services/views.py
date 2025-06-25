# services/views.py
from rest_framework import viewsets, permissions, generics
from .models import Service, CreditTransaction
from .serializers import ServiceSerializer, CreditTransactionSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

class ServiceListView(generics.ListAPIView):
    """
    List all services - accessible to authenticated users
    """
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]  # Changed from IsAdminUser

class ServiceViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for services - admin only
    """
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAdminUser]

class CreditTransactionPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class CreditTransactionListView(generics.ListAPIView):
    serializer_class = CreditTransactionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CreditTransactionPagination

    def get_queryset(self):
        return CreditTransaction.objects.filter(
            user=self.request.user
        ).select_related('service').order_by('-created_at')