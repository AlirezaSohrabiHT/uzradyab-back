# traccar_calls/management/commands/check_expired_devices.py

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.db import connections
from datetime import datetime
import logging
from traccar_calls.models import ExpiredDevice  # Updated model name

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check for expired devices from device_user_db and save them to database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without saving to database',
        )
        parser.add_argument(
            '--max-devices',
            type=int,
            default=4,
            help='Maximum devices per user to process (default: 4)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting expired devices check...'))
        
        try:
            # Get connection to device_user_db
            device_db = connections['device_user_db']  # You'll need to add this to settings
            
            max_devices = options['max_devices']
            current_time = timezone.now()
            
            # Query to get users with their devices and expiration times
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
            
            # Filter expired devices
            expired_devices = []
            total_devices = 0
            
            for user_id, devices in user_devices.items():
                for device in devices:
                    total_devices += 1
                    if device['expirationtime']:
                        try:
                            # Parse expiration time
                            if isinstance(device['expirationtime'], str):
                                expiration_time = datetime.fromisoformat(device['expirationtime'])
                            else:
                                expiration_time = device['expirationtime']
                            
                            # Make timezone aware if needed
                            if expiration_time.tzinfo is None:
                                expiration_time = timezone.make_aware(expiration_time)
                            
                            # Check if expired
                            if expiration_time <= current_time:
                                device['expiration_time_parsed'] = expiration_time
                                expired_devices.append(device)
                                
                        except Exception as e:
                            logger.error(f"Error parsing expiration time for device {device['device_id']}: {e}")
            
            self.stdout.write(f"Found {len(expired_devices)} expired devices out of {total_devices} total devices")
            self.stdout.write(f"Processing devices for {len(user_devices)} users (max {max_devices} devices per user)")
            
            if options['dry_run']:
                self.stdout.write(self.style.WARNING("DRY RUN - Not saving to database"))
                for device in expired_devices:
                    self.stdout.write(
                        f"Would save: User {device['user_name']} -> Device {device['device_name']} "
                        f"(Device ID: {device['device_id']}, Expires: {device['expirationtime']})"
                    )
                return
            
            # Save expired devices to database
            saved_count = 0
            updated_count = 0
            
            for device in expired_devices:
                try:
                    expired_device, created = ExpiredDevice.objects.update_or_create(
                        user_id=device['user_id'],
                        device_id=device['device_id'],
                        defaults={
                            'user_name': device['user_name'] or '',
                            'user_email': device['user_email'] or '',
                            'user_phone': device['user_phone'] or '',
                            'administrator': device['administrator'] or False,
                            'user_disabled': device['user_disabled'] or False,
                            'device_name': device['device_name'] or '',
                            'device_uniqueid': device['uniqueid'] or '',
                            'device_phone': device['device_phone'] or '',
                            'device_disabled': device['device_disabled'] or False,
                            'device_status': device['device_status'] or '',
                            'expiration_time': device['expiration_time_parsed'],
                            'detected_at': timezone.now(),
                        }
                    )
                    
                    if created:
                        saved_count += 1
                        self.stdout.write(
                            f"Saved new: User {device['user_name']} -> Device {device['device_name']}"
                        )
                    else:
                        updated_count += 1
                        self.stdout.write(
                            f"Updated: User {device['user_name']} -> Device {device['device_name']}"
                        )
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error saving device {device['device_id']} for user {device['user_id']}: {e}"
                        )
                    )
            logger.info(f"Completed! Saved: {saved_count}, Updated: {updated_count}")
            self.stdout.write(
                self.style.SUCCESS(
                    f"Completed! Saved: {saved_count}, Updated: {updated_count}"
                )
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in check_expired_devices: {str(e)}"))
            logger.error(f"Error in check_expired_devices command: {str(e)}")