# utils.py
import requests
import json
import logging
from datetime import datetime, timedelta
from django.conf import settings
from .models import Payment, AccountCharge


def update_expiration(device_id, period):
    pass