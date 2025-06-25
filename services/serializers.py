# services/serializers.py
from rest_framework import serializers
from .models import Service, CreditTransaction

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'credit_cost', 'duration_days']

class CreditTransactionSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)
    
    class Meta:
        model = CreditTransaction
        fields = [
            'id', 
            'transaction_type', 
            'amount', 
            'created_at', 
            'description',
            'service_name'
        ]