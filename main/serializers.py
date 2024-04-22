from rest_framework import serializers
from .models import AccountCharge , UserSettings

class AccountChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountCharge
        fields = ('amount', 'duration_days', 'period')

class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = ['id', 'background_color']