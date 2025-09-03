# traccar_calls/management/commands/send_device_expiry_sms.py

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.db import connections
from datetime import datetime
import logging
from traccar_calls.models import ExpiredDevice
from kavenegar import KavenegarAPI, APIException, HTTPException

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send SMS notifications for expired devices at different intervals'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without sending actual SMS',
        )
        parser.add_argument(
            '--force-device',
            type=int,
            help='Force send SMS for specific device ID (for testing)',
        )
        parser.add_argument(
            '--max-devices',
            type=int,
            default=4,
            help='Maximum devices per user to process (default: 4)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting device expiry SMS notifications...'))
        
        try:
            current_date = timezone.now().date()
            device_db = connections['device_user_db']
            max_devices = options['max_devices']
            
            # Get all user-device relationships with expiration times
            query = """
            SELECT 
                u.id as user_id,
                u.name as user_name,
                u.email as user_email,
                u.phone as user_phone,
                u.administrator,
                u.disabled as user_disabled,
                d.id as device_id,
                d.name as device_name,
                d.uniqueid,
                d.phone as device_phone,
                d.expirationtime,
                d.disabled as device_disabled,
                d.status as device_status
            FROM tc_users u
            JOIN tc_user_device ud ON u.id = ud.userid
            JOIN tc_devices d ON ud.deviceid = d.id
            WHERE d.expirationtime IS NOT NULL
            ORDER BY u.id, d.expirationtime
            """
            
            with device_db.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
            
            if not rows:
                self.stdout.write(self.style.WARNING("No devices with expiration time found"))
                return
            
            # Group devices by user and limit to max_devices per user
            user_devices = {}
            for row in rows:
                user_id = row[0]
                device_id = row[6]
                
                # Skip if force-device is specified and this isn't the device
                if options['force_device'] and device_id != options['force_device']:
                    continue
                
                if user_id not in user_devices:
                    user_devices[user_id] = []
                
                if len(user_devices[user_id]) < max_devices:
                    user_devices[user_id].append({
                        'user_id': row[0],
                        'user_name': row[1],
                        'user_email': row[2],
                        'user_phone': row[3],
                        'administrator': row[4],
                        'user_disabled': row[5],
                        'device_id': row[6],
                        'device_name': row[7],
                        'uniqueid': row[8],
                        'device_phone': row[9],
                        'expirationtime': row[10],
                        'device_disabled': row[11],
                        'device_status': row[12],
                    })
                else:
                    self.stdout.write(
                        f"Skipping device {row[7]} for user {row[1]} - exceeds limit of {max_devices} devices"
                    )
            
            total_sms_sent = 0
            total_devices_processed = 0
            
            for user_id, devices in user_devices.items():
                for device_data in devices:
                    if not device_data['expirationtime']:
                        continue
                    
                    total_devices_processed += 1
                    
                    try:
                        # Parse expiration time
                        if isinstance(device_data['expirationtime'], str):
                            expiration_time = datetime.fromisoformat(device_data['expirationtime'])
                        else:
                            expiration_time = device_data['expirationtime']
                        
                        # Make timezone aware if needed
                        if expiration_time.tzinfo is None:
                            expiration_time = timezone.make_aware(expiration_time)
                        
                        expiration_date = expiration_time.date()
                        
                        # Get or create ExpiredDevice record
                        expired_device, created = ExpiredDevice.objects.get_or_create(
                            user_id=device_data['user_id'],
                            device_id=device_data['device_id'],
                            defaults={
                                'user_name': device_data['user_name'] or '',
                                'user_email': device_data['user_email'] or '',
                                'user_phone': device_data['user_phone'] or '',
                                'administrator': device_data['administrator'] or False,
                                'user_disabled': device_data['user_disabled'] or False,
                                'device_name': device_data['device_name'] or '',
                                'device_uniqueid': device_data['uniqueid'] or '',
                                'device_phone': device_data['device_phone'] or '',
                                'device_disabled': device_data['device_disabled'] or False,
                                'device_status': device_data['device_status'] or '',
                                'expiration_time': expiration_time,
                            }
                        )
                        
                        # Update device data if record exists
                        if not created:
                            expired_device.user_name = device_data['user_name'] or ''
                            expired_device.user_email = device_data['user_email'] or ''
                            expired_device.user_phone = device_data['user_phone'] or ''
                            expired_device.device_name = device_data['device_name'] or ''
                            expired_device.device_phone = device_data['device_phone'] or ''
                            expired_device.expiration_time = expiration_time
                            expired_device.save()
                        
                        # Check and send SMS notifications
                        sms_sent = self.check_and_send_sms(
                            expired_device, current_date, expiration_date, options['dry_run']
                        )
                        total_sms_sent += sms_sent
                        
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Error processing device {device_data['device_id']} "
                                f"for user {device_data['user_id']}: {e}"
                            )
                        )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"SMS notifications completed. Processed: {total_devices_processed} devices, "
                    f"Total SMS sent: {total_sms_sent}"
                )
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in send_device_expiry_sms: {str(e)}"))
            logger.error(f"Error in send_device_expiry_sms command: {str(e)}")

    def check_and_send_sms(self, expired_device, current_date, expiration_date, dry_run=False):
        """
        Check and send appropriate SMS based on dates
        """
        sms_sent = 0
        
        # Calculate date differences
        days_to_expire = (expiration_date - current_date).days
        days_after_expire = (current_date - expiration_date).days
        
        # 3 days before expire
        if days_to_expire == 3 and not expired_device.sms_3_days_before_sent:
            if self.send_sms_notification(expired_device, "3 days before expiry", dry_run):
                if not dry_run:
                    expired_device.sms_3_days_before_sent = True
                    expired_device.sms_3_days_before_date = timezone.now()
                    expired_device.save()
                sms_sent += 1
        
        # On expire day
        elif days_to_expire == 0 and not expired_device.sms_expire_day_sent:
            if self.send_sms_notification(expired_device, "expiry day", dry_run):
                if not dry_run:
                    expired_device.sms_expire_day_sent = True
                    expired_device.sms_expire_day_date = timezone.now()
                    expired_device.save()
                sms_sent += 1
        
        # 3 days after expire
        elif days_after_expire == 3 and not expired_device.sms_3_days_after_sent:
            if self.send_sms_notification(expired_device, "3 days after expiry", dry_run):
                if not dry_run:
                    expired_device.sms_3_days_after_sent = True
                    expired_device.sms_3_days_after_date = timezone.now()
                    expired_device.save()
                sms_sent += 1
        
        # 30 days after expire
        elif days_after_expire == 30 and not expired_device.sms_30_days_after_sent:
            if self.send_sms_notification(expired_device, "30 days after expiry", dry_run):
                if not dry_run:
                    expired_device.sms_30_days_after_sent = True
                    expired_device.sms_30_days_after_date = timezone.now()
                    expired_device.save()
                sms_sent += 1
        
        return sms_sent

    def send_sms_notification(self, expired_device, notification_type, dry_run=False):
            """
            Send SMS notification using Kavenegar API
            Fixed to handle spaces in token parameter
            """
            try:
                phone_number = expired_device.get_phone_number()
                
                if not phone_number:
                    self.stdout.write(
                        self.style.WARNING(
                            f"No phone number for user {expired_device.user_name} "
                            f"device {expired_device.device_name}"
                        )
                    )
                    return False
                
                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"DRY RUN: Would send {notification_type} SMS to {phone_number} "
                            f"for user {expired_device.user_name} device {expired_device.device_name}"
                        )
                    )
                    return True
                
                # Initialize Kavenegar API
                api = KavenegarAPI('415270574F5349545265306244503252575A44584C52614C69736C6C56437841')
                
                # Clean up token - remove/replace problematic characters
                # Kavenegar templates don't accept spaces, dashes, or special characters in tokens
                def clean_token(text):
                    if not text:
                        return "نامشخص"  # "Unknown" in Persian
                    # Replace spaces and special characters with underscores
                    cleaned = str(text)
                    cleaned = cleaned.replace(' ', '_')
                    cleaned = cleaned.replace('-', '_') 
                    cleaned = cleaned.replace('/', '_')
                    cleaned = cleaned.replace('\\', '_')
                    cleaned = cleaned.replace('(', '_')
                    cleaned = cleaned.replace(')', '_')
                    cleaned = cleaned.replace('[', '_')
                    cleaned = cleaned.replace(']', '_')
                    cleaned = cleaned.replace('{', '_')
                    cleaned = cleaned.replace('}', '_')
                    cleaned = cleaned.replace('|', '_')
                    cleaned = cleaned.replace('"', '_')
                    cleaned = cleaned.replace("'", '_')
                    cleaned = cleaned.replace('&', '_')
                    cleaned = cleaned.replace('#', '_')
                    cleaned = cleaned.replace('%', '_')
                    cleaned = cleaned.replace('@', '_')
                    cleaned = cleaned.replace('!', '_')
                    cleaned = cleaned.replace('?', '_')
                    cleaned = cleaned.replace('*', '_')
                    cleaned = cleaned.replace('+', '_')
                    cleaned = cleaned.replace('=', '_')
                    cleaned = cleaned.replace('<', '_')
                    cleaned = cleaned.replace('>', '_')
                    # Remove multiple underscores
                    while '__' in cleaned:
                        cleaned = cleaned.replace('__', '_')
                    # Remove leading/trailing underscores
                    cleaned = cleaned.strip('_')
                    return cleaned[:50]  # Limit length to 50 characters
                
                # Create clean tokens
                user_name_clean = clean_token(expired_device.user_name)
                device_name_clean = clean_token(expired_device.device_name)
                
                # Try different token combinations
                token_options = [
                    user_name_clean,  # Just user name
                    device_name_clean,  # Just device name
                    f"{user_name_clean}_{device_name_clean}",  # Both with underscore
                ]
                
                success = False
                last_error = None
                
                for i, token in enumerate(token_options):
                    try:
                        self.stdout.write(f"Trying token option {i+1}: '{token}'")
                        
                        params = {
                            "receptor": phone_number,
                            "template": "uzradyabexpire",
                            "token": token,
                            "type": "sms",
                        }
                        
                        response = api.verify_lookup(params)
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"SMS sent successfully to {phone_number} for user {expired_device.user_name} "
                                f"device {expired_device.device_name} ({notification_type}) with token: '{token}'"
                            )
                        )
                        logger.info(
                            f"SMS sent successfully to {phone_number} for user {expired_device.user_name} "
                            f"device {expired_device.device_name} with token: '{token}'"
                        )
                        success = True
                        break
                        
                    except (APIException, HTTPException) as e:
                        last_error = e
                        error_str = str(e)
                        self.stdout.write(f"Token '{token}' failed: {error_str}")
                        
                        # If still getting 431 error, try next token
                        if "431" in error_str:
                            continue
                        else:
                            # For other errors, don't try more tokens
                            break
                
                # If template SMS failed completely, try regular SMS as fallback
                if not success:
                    try:
                        self.stdout.write("Template SMS failed, trying regular SMS fallback...")
                        
                        # Create a simple message in Persian
                        expiry_date = expired_device.expiration_time.strftime('%Y/%m/%d')
                        message = f"سلام {expired_device.user_name}\nدستگاه {expired_device.device_name} در تاریخ {expiry_date} منقضی شده است.\nلطفا تمدید کنید."
                        
                        response = api.sms_send({
                            "receptor": phone_number,
                            "message": message
                        })
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Regular SMS sent successfully to {phone_number} for user {expired_device.user_name} "
                                f"device {expired_device.device_name} ({notification_type})"
                            )
                        )
                        logger.info(
                            f"Regular SMS sent successfully to {phone_number} for user {expired_device.user_name} "
                            f"device {expired_device.device_name}"
                        )
                        success = True
                        
                    except (APIException, HTTPException) as e:
                        last_error = e
                        self.stdout.write(
                            self.style.ERROR(f"Regular SMS also failed: {str(e)}")
                        )
                
                if not success and last_error:
                    # Decode Persian error message for better logging
                    error_message = str(last_error)
                    try:
                        if hasattr(last_error, 'args') and last_error.args:
                            error_bytes = last_error.args[0]
                            if isinstance(error_bytes, bytes):
                                error_message = error_bytes.decode('utf-8')
                    except:
                        pass
                    
                    self.stdout.write(
                        self.style.ERROR(
                            f"All SMS methods failed for user {expired_device.user_name} "
                            f"device {expired_device.device_name}: {error_message}"
                        )
                    )
                    logger.error(
                        f"All SMS methods failed for user {expired_device.user_name} "
                        f"device {expired_device.device_name}: {error_message}"
                    )
                
                return success
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Unexpected error sending SMS to user {expired_device.user_name} "
                        f"device {expired_device.device_name}: {e}"
                    )
                )
                logger.error(
                    f"Unexpected error sending SMS to user {expired_device.user_name} "
                    f"device {expired_device.device_name}: {e}"
                )
                return False