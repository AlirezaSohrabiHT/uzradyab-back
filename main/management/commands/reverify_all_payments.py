# management/commands/reverify_all_payments.py
from django.core.management.base import BaseCommand
from django.conf import settings
import requests
import json
import time
from main.models import Payment  # Replace 'your_app' with your actual app name
from main.utils import update_expiration  # Replace 'your_app' with your actual app name


class Command(BaseCommand):
    help = 'Reverify all payments with payment codes (one request every 30 seconds)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--status',
            type=str,
            help='Filter by payment status (e.g., "معلق" for pending payments)',
            default=None,
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be reverified without actually doing it',
        )
        parser.add_argument(
            '--delay',
            type=int,
            help='Delay between requests in seconds (default: 30)',
            default=5,
        )
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuously, starting over when all payments are processed',
        )

    def handle(self, *args, **options):
        # Set up Zarinpal URLs based on sandbox setting
        if settings.SANDBOX:
            ZP_API_VERIFY = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
        else:
            ZP_API_VERIFY = "https://api.zarinpal.com/pg/v4/payment/verify.json"

        delay_seconds = options['delay']
        continuous = options['continuous']

        self.stdout.write(f"Starting payment reverification with {delay_seconds} second delay between requests")
        if continuous:
            self.stdout.write("Running in continuous mode - will restart when all payments are processed")

        while True:
            # Filter payments
            payments = Payment.objects.exclude(payment_code="").exclude(payment_code__isnull=True)
            
            if options['status']:
                payments = payments.filter(status=options['status'])
            
            payments = payments.order_by('-timestamp')

            if not payments.exists():
                self.stdout.write("No payments found to reverify")
                if not continuous:
                    break
                self.stdout.write(f"Waiting {delay_seconds} seconds before checking again...")
                time.sleep(delay_seconds)
                continue

            self.stdout.write(f"Found {payments.count()} payments to reverify")

            if options['dry_run']:
                self.stdout.write(self.style.WARNING("DRY RUN - No actual verification will be performed"))
                for payment in payments:
                    self.stdout.write(f"Would reverify Payment ID: {payment.id}, Authority: {payment.payment_code}, Current Status: {payment.status}")
                    if payment != payments.last():  # Don't sleep after the last payment
                        self.stdout.write(f"Waiting {delay_seconds} seconds...")
                        time.sleep(delay_seconds)
                if not continuous:
                    break
                continue

            success_count = 0
            error_count = 0

            for payment in payments:
                try:
                    self.stdout.write(f"Reverifying Payment ID: {payment.id}, Authority: {payment.payment_code}")
                    
                    # Prepare verification data
                    verification_data = {
                        "merchant_id": settings.MERCHANT,
                        "amount": float(payment.amount),
                        "authority": payment.payment_code,
                    }
                    headers = {'content-type': 'application/json'}

                    # Send verification request to Zarinpal
                    response = requests.post(ZP_API_VERIFY, data=json.dumps(verification_data), headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        try:
                            response_data = response.json()
                            
                            # Check if verification was successful
                            if isinstance(response_data.get('data'), dict) and response_data['data'].get('code') in [100, 101]:
                                # Update payment status to successful
                                old_status = payment.status
                                payment.status = "موفق"
                                payment.verification_code = response_data['data']['ref_id']
                                payment.save()

                                # Update expiration if needed
                                try:
                                    update_expiration(payment.device_id_number, payment.account_charge.duration_days)
                                    self.stdout.write(
                                        self.style.SUCCESS(
                                            f"✓ Payment {payment.id} verified successfully. Status changed from '{old_status}' to 'موفق'. RefID: {response_data['data']['ref_id']}"
                                        )
                                    )
                                except Exception as e:
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f"✓ Payment {payment.id} verified but expiration update failed: {str(e)}"
                                        )
                                    )
                                success_count += 1
                            else:
                                # Handle unsuccessful verification
                                code = response_data['data'].get('code') if isinstance(response_data.get('data'), dict) else 'invalid response format'
                                old_status = payment.status
                                payment.status = "ناموفق"
                                payment.save()
                                self.stdout.write(
                                    self.style.ERROR(
                                        f"✗ Payment {payment.id} verification failed. Status changed from '{old_status}' to 'ناموفق'. Code: {code}"
                                    )
                                )
                                error_count += 1
                        except ValueError:
                            self.stdout.write(self.style.ERROR(f"✗ Payment {payment.id}: Invalid JSON response"))
                            error_count += 1
                    else:
                        self.stdout.write(self.style.ERROR(f"✗ Payment {payment.id}: HTTP {response.status_code}"))
                        error_count += 1

                except requests.exceptions.Timeout:
                    self.stdout.write(self.style.ERROR(f"✗ Payment {payment.id}: Request timeout"))
                    error_count += 1
                except requests.exceptions.ConnectionError:
                    self.stdout.write(self.style.ERROR(f"✗ Payment {payment.id}: Connection error"))
                    error_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"✗ Payment {payment.id}: Unexpected error - {str(e)}"))
                    error_count += 1

                # Wait 30 seconds before processing next payment (except for the last one)
                if payment != payments.last():
                    self.stdout.write(f"Waiting {delay_seconds} seconds before next verification...")
                    time.sleep(delay_seconds)
                elif continuous:
                    self.stdout.write(f"Batch completed. Waiting {delay_seconds} seconds before starting over...")
                    time.sleep(delay_seconds)

            # Summary for this batch
            self.stdout.write("\n" + "="*50)
            self.stdout.write(f"BATCH SUMMARY:")
            self.stdout.write(f"Total processed: {success_count + error_count}")
            self.stdout.write(self.style.SUCCESS(f"Successful: {success_count}"))
            self.stdout.write(self.style.ERROR(f"Failed: {error_count}"))
            self.stdout.write("="*50)

            if not continuous:
                break