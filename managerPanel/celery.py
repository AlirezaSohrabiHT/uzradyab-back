# managerPanel/celery.py - Update your existing celery.py

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'managerPanel.settings')

app = Celery('managerPanel')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Periodic tasks configuration
app.conf.beat_schedule = {
    'check-expired-users-midnight': {
        'task': 'traccar_calls.tasks.check_expired_users',  # Replace 'your_app' with actual app name
        'schedule': crontab(hour=0, minute=20),  # Every day at midnight
    },
    'send-expiry-sms-notifications': {
        'task': 'traccar_calls.tasks.send_expiry_sms_notifications',
        'schedule': crontab(hour=9, minute=0),  # Every day at 9 AM
    },
    'cleanup-old-expired-users-weekly': {
        'task': 'traccar_calls.tasks.cleanup_old_expired_users',  # Replace 'your_app' with actual app name
        'schedule': crontab(hour=2, minute=0, day_of_week=0),  # Every Sunday at 2 AM
        'kwargs': {'days': 30},  # Keep records for 30 days
    },
}

app.conf.timezone = 'Asia/Tehran'