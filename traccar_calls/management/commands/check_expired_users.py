# traccar_calls/management/commands/check_expired_users.py

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from datetime import datetime
import requests
import logging
from traccar_calls.models import ExpiredUser

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check for expired users from Traccar API and save them to database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without saving to database',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting expired users check...'))
        
        try:
            # Get all users from Traccar API
            users = self.fetch_all_traccar_users()
            
            if not users:
                self.stdout.write(self.style.WARNING("No users found from Traccar API"))
                return
            
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
            
            self.stdout.write(f"Found {len(expired_users)} expired users out of {len(users)} total users")
            
            if options['dry_run']:
                self.stdout.write(self.style.WARNING("DRY RUN - Not saving to database"))
                for user in expired_users:
                    self.stdout.write(f"Would save: {user.get('name')} (ID: {user.get('id')})")
                return
            
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
                        self.stdout.write(f"Saved new expired user: {user.get('name')}")
                    else:
                        updated_count += 1
                        self.stdout.write(f"Updated expired user: {user.get('name')}")
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error saving expired user {user.get('id')}: {e}")
                    )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Completed! Saved: {saved_count}, Updated: {updated_count}"
                )
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in check_expired_users: {str(e)}"))
            logger.error(f"Error in check_expired_users command: {str(e)}")

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