from rest_framework import serializers
from .models import AccountCharge , UserSettings , Payment

class AccountChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountCharge
        fields = ('id', 'amount', 'duration_days', 'period')

class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = ['id', 'background_color']
        
class PaymentSerializer(serializers.ModelSerializer):
    account_charge = AccountChargeSerializer(read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'unique_id', 'name', 'device_id_number', 'phone', 
            'period', 'amount', 'payment_code', 'verification_code', 
            'status', 'timestamp', 'account_charge'
        ]