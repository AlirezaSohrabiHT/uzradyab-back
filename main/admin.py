from django.contrib import admin
from .models import Payment , AccountCharge

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('unique_id', 'name', 'id_number', 'phone', 'period', 'amount' , 'payment_code' , 'verification_code' , 'timestamp')
    list_filter = ('timestamp',)  # Optional: Add filters for timestamp
    search_fields = ('unique_id', 'name', 'id_number')  # Optional: Add search fields

admin.site.register(Payment, PaymentAdmin)

class AccountChargeAdmin(admin.ModelAdmin):
    list_display = ('period', 'amount', 'duration_months', 'timestamp')
    search_fields = ('period', 'amount')
    list_filter = ('period', 'timestamp')

admin.site.register(AccountCharge, AccountChargeAdmin)