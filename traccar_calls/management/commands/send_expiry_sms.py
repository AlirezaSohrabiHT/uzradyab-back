# traccar_calls/management/commands/send_expiry_sms.py

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from datetime import datetime
import requests
import logging
from traccar_calls.models import ExpiredUser
from kavenegar import KavenegarAPI, APIException, HTTPException

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send SMS notifications for expired users at different intervals'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without sending actual SMS',
        )
        parser.add_argument(
            '--force-user',
            type=int,
            help='Force send SMS for specific user ID (for testing)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting expiry SMS notifications...'))
        
        try:
            current_date = timezone.now().date()
            
            # Get all users from Traccar API to check current status
            all_users = self.fetch_all_traccar_users()
            
            if not all_users:
                self.stdout.write(self.style.WARNING("No users found from Traccar API"))
                return
            
            total_sms_sent = 0
            
            for user_data in all_users:
                if not user_data.get('expirationTime'):
                    continue
                
                # Skip if force-user is specified and this isn't the user
                if options['force_user'] and user_data.get('id') != options['force_user']:
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
                    sms_sent = self.check_and_send_sms(
                        expired_user, current_date, expiration_date, options['dry_run']
                    )
                    total_sms_sent += sms_sent
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error processing user {user_data.get('id')}: {e}")
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f"SMS notifications completed. Total SMS sent: {total_sms_sent}")
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in send_expiry_sms: {str(e)}"))
            logger.error(f"Error in send_expiry_sms command: {str(e)}")

    def check_and_send_sms(self, expired_user, current_date, expiration_date, dry_run=False):
        """
        Check and send appropriate SMS based on dates
        """
        sms_sent = 0
        
        # Calculate date differences
        days_to_expire = (expiration_date - current_date).days
        days_after_expire = (current_date - expiration_date).days
        
        # 3 days before expire
        if days_to_expire == 3 and not expired_user.sms_3_days_before_sent:
            if self.send_sms_notification(expired_user, "3 days before expiry", dry_run):
                if not dry_run:
                    expired_user.sms_3_days_before_sent = True
                    expired_user.save()
                sms_sent += 1
        
        # On expire day
        elif days_to_expire == 0 and not expired_user.sms_expire_day_sent:
            if self.send_sms_notification(expired_user, "expiry day", dry_run):
                if not dry_run:
                    expired_user.sms_expire_day_sent = True
                    expired_user.save()
                sms_sent += 1
        
        # 3 days after expire
        elif days_after_expire == 3 and not expired_user.sms_3_days_after_sent:
            if self.send_sms_notification(expired_user, "3 days after expiry", dry_run):
                if not dry_run:
                    expired_user.sms_3_days_after_sent = True
                    expired_user.save()
                sms_sent += 1
        
        # 30 days after expire
        elif days_after_expire == 30 and not expired_user.sms_30_days_after_sent:
            if self.send_sms_notification(expired_user, "30 days after expiry", dry_run):
                if not dry_run:
                    expired_user.sms_30_days_after_sent = True
                    expired_user.save()
                sms_sent += 1
        
        return sms_sent

    def send_sms_notification(self, expired_user, notification_type, dry_run=False):
        """
        Send SMS notification using Kavenegar API
        """
        try:
            phone_number = expired_user.get_phone_number()
            
            if not phone_number:
                self.stdout.write(
                    self.style.WARNING(f"No phone number for user {expired_user.name}")
                )
                return False
            
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"DRY RUN: Would send {notification_type} SMS to {phone_number} "
                        f"for user {expired_user.name}"
                    )
                )
                return True
            
            # Initialize Kavenegar API
            api = KavenegarAPI('415270574F5349545265306244503252575A44584C52614C69736C6C56437841')
            
            params = {
                "receptor": phone_number,
                "template": "uzradyabexpire",
                "token": expired_user.name,
                "type": "sms",
            }
            
            response = api.verify_lookup(params)
            self.stdout.write(
                self.style.SUCCESS(
                    f"SMS sent successfully to {phone_number} for user {expired_user.name} "
                    f"({notification_type})"
                )
            )
            logger.info(f"SMS sent successfully to {phone_number} for user {expired_user.name}")
            return True
            
        except (APIException, HTTPException) as e:
            self.stdout.write(
                self.style.ERROR(f"Kavenegar API error for user {expired_user.name}: {e}")
            )
            logger.error(f"Kavenegar API error for user {expired_user.name}: {e}")
            return False
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error sending SMS to user {expired_user.name}: {e}")
            )
            logger.error(f"Error sending SMS to user {expired_user.name}: {e}")
            return False

    def fetch_all_traccar_users(self):
        """
        Fetch all users from Traccar API using Basic Auth.
        """
        base_url = settings.TRACCAR_API_URL
        auth = (settings.TRACCAR_API_USERNAME, settings.TRACCAR_API_PASSWORD)
        
        try:
            users_url = f"{base_url}/users"
            response = requests.get(users_url, auth=auth, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to fetch users from Traccar: {response.status_code} - {response.text}"
                    )
                )
                return []
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching users from Traccar API: {str(e)}"))
            return []