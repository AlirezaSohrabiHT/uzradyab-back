from django.core.management.base import BaseCommand
from django.db import connections
from django.utils import timezone
from uzradyabHandler.models import ExpiredDevice

class Command(BaseCommand):
    help = 'Sync expired devices from the original database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ignore-phones',
            nargs='*',
            help='Phone numbers to ignore (space separated)',
            default=[]
        )

    def handle(self, *args, **options):
        current_time = timezone.now()
        
        # Define phone numbers to ignore
        # You can modify this list or pass via command arguments
        ignored_phone_numbers = set([
            # Device phone numbers to ignore
            '09154284393',
            '09150000000',
            'modir@exir.com',
            # Add more phone numbers here
        ])
        
        # Add phone numbers from command arguments
        if options['ignore_phones']:
            ignored_phone_numbers.update(options['ignore_phones'])
        
        # Also ignore users with these phone numbers
        ignored_user_phones = set([
            '09154284393',
            '09150000000',
            'modir@exir.com'
            # Add user phone numbers to ignore
        ])
        
        # Remove empty strings and None values
        ignored_phone_numbers = {phone for phone in ignored_phone_numbers if phone}
        ignored_user_phones = {phone for phone in ignored_user_phones if phone}
        
        self.stdout.write(f'Ignoring devices with phones: {ignored_phone_numbers}')
        self.stdout.write(f'Ignoring users with phones: {ignored_user_phones}')
        
        with connections['device_user_db'].cursor() as cursor:
            query = """
                SELECT 
                    d.id, d.name, d.uniqueid, d.phone, d.expirationtime,
                    u.email, u.phone as user_phone
                FROM 
                    tc_devices d
                JOIN 
                    tc_user_device ud ON d.id = ud.deviceid
                JOIN 
                    tc_users u ON ud.userid = u.id
                WHERE 
                    d.expirationtime IS NOT NULL
                    AND d.expirationtime < %s
                ORDER BY d.expirationtime DESC
            """
            cursor.execute(query, [current_time])
            expired_devices_data = cursor.fetchall()

        # Group devices and users with filtering
        devices_dict = {}
        ignored_devices_count = 0
        ignored_users_count = 0
        
        for device in expired_devices_data:
            device_id = device[0]
            device_phone = device[3]
            user_phone = device[6]
            
            # Skip devices with ignored phone numbers
            if device_phone and device_phone in ignored_phone_numbers:
                ignored_devices_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Ignored device {device[1]} with phone {device_phone}')
                )
                continue
            
            # Initialize device data if not exists
            if device_id not in devices_dict:
                devices_dict[device_id] = {
                    "device_id": device[0],
                    "name": device[1],
                    "uniqueid": device[2],
                    "phone": device_phone,
                    "expirationtime": device[4],
                    "user_emails": [],
                    "user_phones": [],
                }
            
            # Add user details, but skip ignored user phone numbers
            if device[5]:  # email
                devices_dict[device_id]["user_emails"].append(device[5])
                
            if user_phone:  # user phone
                if user_phone not in ignored_user_phones:
                    devices_dict[device_id]["user_phones"].append(user_phone)
                else:
                    ignored_users_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'Ignored user phone {user_phone} for device {device[1]}')
                    )

        # Filter out devices that have no valid users after filtering
        filtered_devices_dict = {}
        for device_id, device_data in devices_dict.items():
            # Keep device if it has at least one email or one valid phone
            if device_data["user_emails"] or device_data["user_phones"]:
                filtered_devices_dict[device_id] = device_data
            else:
                self.stdout.write(
                    self.style.WARNING(f'Removed device {device_data["name"]} - no valid users remaining')
                )

        # Create or update ExpiredDevice records
        created_count = 0
        updated_count = 0
        
        for device_data in filtered_devices_dict.values():
            # Remove duplicates from lists
            device_data["user_emails"] = list(set(device_data["user_emails"]))
            device_data["user_phones"] = list(set(device_data["user_phones"]))
            
            expired_device, created = ExpiredDevice.objects.update_or_create(
                device_id=device_data["device_id"],
                expirationtime=device_data["expirationtime"],
                defaults={
                    'name': device_data["name"],
                    'uniqueid': device_data["uniqueid"],
                    'phone': device_data["phone"],
                    'user_emails': device_data["user_emails"],
                    'user_phones': device_data["user_phones"],
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully synced expired devices: {created_count} created, {updated_count} updated'
            )
        )
        self.stdout.write(
            self.style.WARNING(
                f'Ignored: {ignored_devices_count} devices, {ignored_users_count} user phones'
            )
        )