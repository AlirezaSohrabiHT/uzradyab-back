# tasks.py
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from datetime import datetime
import requests
import logging
from .models import ExpiredUser
from kavenegar import KavenegarAPI, APIException, HTTPException
logger = logging.getLogger(__name__)

@shared_task
def check_expired_users():
    """
    Check for expired users from Traccar API and save them to database.
    Runs daily at midnight.
    """
    logger.info("Starting expired users check task...")
    
    try:
        # Get all users from Traccar API
        users = fetch_all_traccar_users()
        
        if not users:
            logger.warning("No users found from Traccar API")
            return "No users found"
        
        # Filter expired users
        current_time = timezone.now()
        expired_users = []
        
        for user in users:
            expiration_time_str = user.get('expirationTime')
            if expiration_time_str:
                try:
                    # Parse expiration time
                    expiration_time = datetime.fromisoformat(
                        expiration_time_str.replace('Z', '+00:00')
                    )
                    
                    # Check if expired
                    if expiration_time <= current_time:
                        expired_users.append(user)
                        
                except Exception as e:
                    logger.error(f"Error parsing expiration time for user {user.get('id')}: {e}")
        
        # Save expired users to database
        saved_count = 0
        updated_count = 0
        
        for user in expired_users:
            try:
                expiration_time = datetime.fromisoformat(
                    user.get('expirationTime').replace('Z', '+00:00')
                )
                
                expired_user, created = ExpiredUser.objects.update_or_create(
                    traccar_user_id=user.get('id'),
                    defaults={
                        'name': user.get('name', ''),
                        'email': user.get('email', ''),
                        'phone': user.get('phone', ''),
                        'administrator': user.get('administrator', False),
                        'disabled': user.get('disabled', False),
                        'expiration_time': expiration_time,
                        'device_limit': user.get('deviceLimit', 0),
                        'user_limit': user.get('userLimit', 0),
                        'detected_at': timezone.now(),
                    }
                )
                
                if created:
                    saved_count += 1
                else:
                    updated_count += 1
                    
            except Exception as e:
                logger.error(f"Error saving expired user {user.get('id')}: {e}")
        
        result_message = f"Expired users check completed. Total users: {len(users)}, Expired: {len(expired_users)}, Saved: {saved_count}, Updated: {updated_count}"
        logger.info(result_message)
        return result_message
        
    except Exception as e:
        error_message = f"Error in check_expired_users task: {str(e)}"
        logger.error(error_message)
        return error_message

def fetch_all_traccar_users():
    """
    Fetch all users from Traccar API using Basic Auth.
    Same logic as CheckUserExistsView.
    """
    base_url = settings.TRACCAR_API_URL
    auth = (settings.TRACCAR_API_USERNAME, settings.TRACCAR_API_PASSWORD)
    
    try:
        users_url = f"{base_url}/users"
        response = requests.get(users_url, auth=auth, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to fetch users from Traccar: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"Error fetching users from Traccar API: {str(e)}")
        return []

@shared_task
def cleanup_old_expired_users(days=30):
    """
    Clean up old expired user records.
    Keep only records from the last X days.
    """
    try:
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        deleted_count = ExpiredUser.objects.filter(detected_at__lt=cutoff_date).count()
        ExpiredUser.objects.filter(detected_at__lt=cutoff_date).delete()
        
        logger.info(f"Cleaned up {deleted_count} old expired user records older than {days} days")
        return f"Cleaned up {deleted_count} old records"
        
    except Exception as e:
        error_message = f"Error in cleanup_old_expired_users task: {str(e)}"
        logger.error(error_message)
        return error_message

@shared_task
def send_expiry_sms_notifications():
    """
    Send SMS notifications for expired users at different intervals:
    - 3 days before expire
    - On expire day  
    - 3 days after expire
    - 30 days after expire
    """
    logger.info("Starting expiry SMS notifications task...")
    
    try:
        current_date = timezone.now().date()
        
        # Get all users from Traccar API to check current status
        all_users = fetch_all_traccar_users()
        user_dict = {user['id']: user for user in all_users}
        
        # Process each user for SMS notifications
        total_sms_sent = 0
        
        for user_data in all_users:
            if not user_data.get('expirationTime'):
                continue
                
            try:
                expiration_time = datetime.fromisoformat(
                    user_data.get('expirationTime').replace('Z', '+00:00')
                )
                expiration_date = expiration_time.date()
                
                # Get or create ExpiredUser record
                expired_user, created = ExpiredUser.objects.get_or_create(
                    traccar_user_id=user_data.get('id'),
                    defaults={
                        'name': user_data.get('name', ''),
                        'email': user_data.get('email', ''),
                        'phone': user_data.get('phone', ''),
                        'administrator': user_data.get('administrator', False),
                        'disabled': user_data.get('disabled', False),
                        'expiration_time': expiration_time,
                        'device_limit': user_data.get('deviceLimit', 0),
                        'user_limit': user_data.get('userLimit', 0),
                    }
                )
                
                # Update user data if record exists
                if not created:
                    expired_user.name = user_data.get('name', '')
                    expired_user.email = user_data.get('email', '')
                    expired_user.phone = user_data.get('phone', '')
                    expired_user.expiration_time = expiration_time
                    expired_user.save()
                
                # Check and send SMS notifications
                sms_sent = check_and_send_sms(expired_user, current_date, expiration_date)
                total_sms_sent += sms_sent
                
            except Exception as e:
                logger.error(f"Error processing user {user_data.get('id')}: {e}")
        
        result_message = f"SMS notifications task completed. Total SMS sent: {total_sms_sent}"
        logger.info(result_message)
        return result_message
        
    except Exception as e:
        error_message = f"Error in send_expiry_sms_notifications task: {str(e)}"
        logger.error(error_message)
        return error_message

def check_and_send_sms(expired_user, current_date, expiration_date):
    """
    Check and send appropriate SMS based on dates
    """
    sms_sent = 0
    
    # Calculate date differences
    days_to_expire = (expiration_date - current_date).days
    days_after_expire = (current_date - expiration_date).days
    
    # 3 days before expire
    if days_to_expire == 3 and not expired_user.sms_3_days_before_sent:
        if send_sms_notification(expired_user):
            expired_user.sms_3_days_before_sent = True
            expired_user.save()
            sms_sent += 1
            logger.info(f"Sent 3-days-before SMS to {expired_user.name}")
    
    # On expire day
    elif days_to_expire == 0 and not expired_user.sms_expire_day_sent:
        if send_sms_notification(expired_user):
            expired_user.sms_expire_day_sent = True
            expired_user.save()
            sms_sent += 1
            logger.info(f"Sent expire-day SMS to {expired_user.name}")
    
    # 3 days after expire
    elif days_after_expire == 3 and not expired_user.sms_3_days_after_sent:
        if send_sms_notification(expired_user):
            expired_user.sms_3_days_after_sent = True
            expired_user.save()
            sms_sent += 1
            logger.info(f"Sent 3-days-after SMS to {expired_user.name}")
    
    # 30 days after expire
    elif days_after_expire == 30 and not expired_user.sms_30_days_after_sent:
        if send_sms_notification(expired_user):
            expired_user.sms_30_days_after_sent = True
            expired_user.save()
            sms_sent += 1
            logger.info(f"Sent 30-days-after SMS to {expired_user.name}")
    
    return sms_sent

def send_sms_notification(expired_user):
    """
    Send SMS notification using Kavenegar API
    """
    try:
        phone_number = expired_user.get_phone_number()
        
        if not phone_number:
            logger.warning(f"No phone number for user {expired_user.name}")
            return False
        
        # Initialize Kavenegar API
        api = KavenegarAPI('415270574F5349545265306244503252575A44584C52614C69736C6C56437841')
        
        params = {
            "receptor": phone_number,
            "template": "uzradyabexpire",
            "token": expired_user.name,
            "type": "sms",
        }
        
        response = api.verify_lookup(params)
        logger.info(f"SMS sent successfully to {phone_number} for user {expired_user.name}")
        return True
        
    except (APIException, HTTPException) as e:
        logger.error(f"Kavenegar API error for user {expired_user.name}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending SMS to user {expired_user.name}: {e}")
        return False