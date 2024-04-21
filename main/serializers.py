from rest_framework import serializers
from .models import AccountCharge

class AccountChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountCharge
        fields = ('amount', 'duration_days', 'period')