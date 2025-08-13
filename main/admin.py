from django.contrib import admin
from jalali_date import datetime2jalali
from jalali_date.admin import ModelAdminJalaliMixin, StackedInlineJalaliMixin, TabularInlineJalaliMixin
from .models import Payment, AccountCharge

class PaymentAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = (
        'account_charge','unique_id', 'name', 'status', 'device_id_number', 'phone', 
        'period', 'amount', 'payment_code', 'verification_code', 'get_jalali_timestamp'
    )
    list_filter = ('status', 'timestamp')
    search_fields = ('unique_id', 'name', 'device_id_number')

    def get_jalali_timestamp(self, obj):
        return datetime2jalali(obj.timestamp).strftime('%Y/%m/%d %H:%M')
    get_jalali_timestamp.short_description = 'زمان (جلالی)'

admin.site.register(Payment, PaymentAdmin)

class AccountChargeAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('period', 'amount', 'duration_days', 'get_jalali_timestamp')
    search_fields = ('period', 'amount')
    list_filter = ('period', 'timestamp')

    def get_jalali_timestamp(self, obj):
        return datetime2jalali(obj.timestamp).strftime('%Y/%m/%d %H:%M')
    get_jalali_timestamp.short_description = 'زمان (جلالی)'

admin.site.register(AccountCharge, AccountChargeAdmin)
