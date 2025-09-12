from celery import shared_task
from django.core.management import call_command

@shared_task
def run_check_expired_devices():
    call_command("check_expired_devices")

@shared_task
def run_send_device_expiry_sms():
    call_command("send_device_expiry_sms")
