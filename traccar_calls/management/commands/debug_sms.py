# traccar_calls/management/commands/debug_sms.py

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
import requests
import logging
from traccar_calls.models import ExpiredUser

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Debug SMS notifications - show detailed info about users and their SMS status'

    def add_arguments(self, parser):
        parser.add_argument(
            '--show-all',
            action='store_true',
            help='Show all users, not just ones needing SMS',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== SMS NOTIFICATION DEBUG ==='))
        
        current_date = timezone.now().date()
        current_time = timezone.now()
        
        self.stdout.write(f"Current date: {current_date}")
        self.stdout.write(f"Current time: {current_time}")
        self.stdout.write("")
        
        # Check database records first
        self.stdout.write(self.style.WARNING("=== DATABASE RECORDS ==="))
        db_users = ExpiredUser.objects.all().order_by('-detected_at')
        
        if not db_users.exists():
            self.stdout.write(self.style.ERROR("No ExpiredUser records found in database!"))
            return
            
        self.stdout.write(f"Found {db_users.count()} expired users in database:")
        
        for user in db_users:
            self.stdout.write(f"\n--- User: {user.name} (ID: {user.traccar_user_id}) ---")
            self.stdout.write(f"Phone: {user.phone}")
            self.stdout.write(f"Expiration: {user.expiration_time}")
            self.stdout.write(f"Detected at: {user.detected_at}")
            
            if user.expiration_time:
                exp_date = user.expiration_time.date()
                days_to_expire = (exp_date - current_date).days
                days_after_expire = (current_date - exp_date).days
                
                self.stdout.write(f"Days to expire: {days_to_expire}")
                self.stdout.write(f"Days after expire: {days_after_expire}")
                
                # SMS status
                self.stdout.write("SMS Status:")
                self.stdout.write(f"  - 3 days before: {user.sms_3_days_before_sent}")
                self.stdout.write(f"  - Expire day: {user.sms_expire_day_sent}")
                self.stdout.write(f"  - 3 days after: {user.sms_3_days_after_sent}")
                self.stdout.write(f"  - 30 days after: {user.sms_30_days_after_sent}")
                
                # Check if SMS should be sent
                should_send_sms = False
                sms_type = ""
                
                if days_to_expire == 3 and not user.sms_3_days_before_sent:
                    should_send_sms = True
                    sms_type = "3 days before expiry"
                elif days_to_expire == 0 and not user.sms_expire_day_sent:
                    should_send_sms = True
                    sms_type = "expire day"
                elif days_after_expire == 3 and not user.sms_3_days_after_sent:
                    should_send_sms = True
                    sms_type = "3 days after expiry"
                elif days_after_expire == 30 and not user.sms_30_days_after_sent:
                    should_send_sms = True
                    sms_type = "30 days after expiry"
                
                if should_send_sms:
                    self.stdout.write(self.style.SUCCESS(f"*** SHOULD SEND SMS: {sms_type} ***"))
                else:
                    self.stdout.write("No SMS needed for this user today")
        
        # Now check Traccar API
        self.stdout.write(self.style.WARNING("\n=== TRACCAR API CHECK ==="))
        
        try:
            all_users = self.fetch_all_traccar_users()
            
            if not all_users:
                self.stdout.write(self.style.ERROR("No users found from Traccar API!"))
                return
                
            self.stdout.write(f"Found {len(all_users)} users from Traccar API")
            
            users_with_expiry = [u for u in all_users if u.get('expirationTime')]
            self.stdout.write(f"Users with expiration time: {len(users_with_expiry)}")
            
            for user_data in users_with_expiry[:5]:  # Show first 5
                self.stdout.write(f"\nTraccar User: {user_data.get('name')} (ID: {user_data.get('id')})")
                self.stdout.write(f"Phone: {user_data.get('phone')}")
                self.stdout.write(f"Expiration: {user_data.get('expirationTime')}")
                
                # Parse expiration time
                try:
                    expiration_time = datetime.fromisoformat(
                        user_data.get('expirationTime').replace('Z', '+00:00')
                    )
                    exp_date = expiration_time.date()
                    days_to_expire = (exp_date - current_date).days
                    days_after_expire = (current_date - exp_date).days
                    
                    self.stdout.write(f"Days to expire: {days_to_expire}")
                    self.stdout.write(f"Days after expire: {days_after_expire}")
                    
                    # Check if this user exists in database
                    try:
                        db_user = ExpiredUser.objects.get(traccar_user_id=user_data.get('id'))
                        self.stdout.write("✓ User exists in database")
                    except ExpiredUser.DoesNotExist:
                        self.stdout.write("✗ User NOT in database")
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error parsing expiration: {e}"))
            
            if len(users_with_expiry) > 5:
                self.stdout.write(f"\n... and {len(users_with_expiry) - 5} more users")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching from Traccar: {e}"))
        
        # Test scenarios
        self.stdout.write(self.style.WARNING("\n=== TEST SCENARIOS ==="))
        self.stdout.write("To test SMS for specific scenarios, you can temporarily:")
        self.stdout.write("1. Modify expiration_time in database to test different date ranges")
        self.stdout.write("2. Reset SMS flags to False for testing")
        self.stdout.write("3. Use --force-user parameter with specific user ID")
        
        # SQL commands for testing
        self.stdout.write("\nSQL commands for testing:")
        self.stdout.write("-- Reset all SMS flags for testing")
        self.stdout.write("UPDATE traccar_calls_expireduser SET sms_3_days_before_sent=0, sms_expire_day_sent=0, sms_3_days_after_sent=0, sms_30_days_after_sent=0;")
        
        self.stdout.write("\n-- Set expiration to 3 days from now for testing")
        current_plus_3 = (current_time + timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
        self.stdout.write(f"UPDATE traccar_calls_expireduser SET expiration_time='{current_plus_3}' WHERE id=1;")

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