from django.db import models


class Payment(models.Model):

    PAYMENT_METHOD_CHOICES = [
        ("credit", "اعتبار"),
        ("gateway", "درگاه پرداخت"),
    ]

    user = models.ForeignKey('accounts.User', on_delete = models.CASCADE, null = True, blank = True)
    unique_id = models.CharField(max_length=100, verbose_name="شناسه یکتا", null = True, blank = True)
    name = models.CharField(max_length=100, verbose_name="نام", null = True, blank = True)
    device_id_number = models.CharField(max_length=100, verbose_name="شناسه دستگاه", default="")
    phone = models.CharField(max_length=50, verbose_name="شماره تلفن", default="")
    period = models.CharField(max_length=100, verbose_name="مدت زمان", default="")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="مقدار پرداخت", default=None)
    payment_code = models.CharField(max_length=100, verbose_name="کد پرداخت", default="")
    verification_code = models.CharField(max_length=100, verbose_name="کد تایید", default="")
    status = models.CharField(max_length=100, verbose_name="وضعیت پرداخت", default="")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="زمان")
    account_charge = models.ForeignKey('AccountCharge', on_delete=models.CASCADE, related_name='payments', verbose_name="شارژ حساب", null=True, blank=True)
    imei = models.CharField(max_length = 50, verbose_name="سریال دستگاه", null = True, blank = True)
    method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, verbose_name='روش پرداخت', null = True, blank = True)

    def __str__(self):
        return f"Payment of {self.amount} at {self.timestamp}"

    class Meta:
        verbose_name = "پرداخت"
        verbose_name_plural = "پرداخت"

class AccountCharge(models.Model):
    period = models.CharField(max_length=100, verbose_name="دوره", default="")
    description = models.CharField(max_length=100, verbose_name="توضیحات", default="")
    amount = models.DecimalField(max_digits=20, decimal_places=0, verbose_name="هزینه (ریال)", default=None, null=True)
    credit_cost = models.PositiveIntegerField()
    phone = models.DecimalField(max_digits=11, decimal_places=0, verbose_name="تلفن برای درگاه پرداخت", default=None, null=True, blank=True)
    duration_days = models.IntegerField(verbose_name="مدت اعتبار (روز)", default=1)
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="زمان")

    def __str__(self):
        return f"دوره {self.period}"

    class Meta:
        verbose_name = "شارژ حساب"
        verbose_name_plural = "تنظیمات شارژ حساب‌ها"

class UserSettings(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    background_color = models.CharField(max_length=20)  # You can adjust the max length as needed
    
    def __str__(self):
        return f"Settings for {self.id}"


