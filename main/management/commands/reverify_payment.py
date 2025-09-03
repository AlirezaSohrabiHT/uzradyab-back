# management/commands/reverify_payment.py
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import requests
import json
from main.models import Payment  # Replace 'your_app' with your actual app name
from main.utils import update_expiration  # Replace 'your_app' with your actual app name


class Command(BaseCommand):
    help = 'Reverify a specific payment by ID'

    def add_arguments(self, parser):
        parser.add_argument(
            'payment_id',
            type=int,
            help='The ID of the payment to reverify'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be reverified without actually doing it',
        )

    def handle(self, *args, **options):
        payment_id = options['payment_id']

        # Set up Zarinpal URLs based on sandbox setting
        if settings.SANDBOX:
            ZP_API_VERIFY = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
        else:
            ZP_API_VERIFY = "https://api.zarinpal.com/pg/v4/payment/verify.json"

        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist:
            raise CommandError(f'Payment with ID "{payment_id}" does not exist.')

        # Check if payment has a payment code
        if not payment.payment_code:
            raise CommandError(f'Payment with ID "{payment_id}" does not have a payment code.')

        self.stdout.write(f"Payment Details:")
        self.stdout.write(f"  ID: {payment.id}")
        self.stdout.write(f"  Authority: {payment.payment_code}")
        self.stdout.write(f"  Amount: {payment.amount}")
        self.stdout.write(f"  Current Status: {payment.status}")
        self.stdout.write(f"  Device ID: {payment.device_id_number}")
        self.stdout.write(f"  Phone: {payment.phone}")
        self.stdout.write(f"  Period: {payment.period}")

        if options['dry_run']:
            self.stdout.write(self.style.WARNING("DRY RUN - No actual verification will be performed"))
            return

        try:
            self.stdout.write(f"\nReverifying payment...")
            
            # Prepare verification data
            verification_data = {
                "merchant_id": settings.MERCHANT,
                "amount": float(payment.amount),
                "authority": payment.payment_code,
            }
            headers = {'content-type': 'application/json'}

            self.stdout.write(f"Sending verification request to Zarinpal...")

            # Send verification request to Zarinpal
            response = requests.post(ZP_API_VERIFY, data=json.dumps(verification_data), headers=headers, timeout=10)
            
            self.stdout.write(f"Response status code: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    self.stdout.write(f"Response data: {json.dumps(response_data, indent=2)}")
                    
                    # Check if verification was successful
                    if isinstance(response_data.get('data'), dict) and response_data['data'].get('code') in [100, 101]:
                        # Update payment status to successful
                        old_status = payment.status
                        payment.status = "موفق"
                        payment.verification_code = response_data['data']['ref_id']
                        payment.save()

                        # Update expiration if needed
                        try:
                            update_expiration(payment.device_id_number, payment.period)
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"\n✓ Payment {payment.id} verified successfully!"
                                )
                            )
                            self.stdout.write(f"  Status changed from '{old_status}' to 'موفق'")
                            self.stdout.write(f"  RefID: {response_data['data']['ref_id']}")
                            self.stdout.write(f"  Expiration updated for device: {payment.device_id_number}")
                        except Exception as e:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"\n✓ Payment {payment.id} verified successfully!"
                                )
                            )
                            self.stdout.write(f"  Status changed from '{old_status}' to 'موفق'")
                            self.stdout.write(f"  RefID: {response_data['data']['ref_id']}")
                            self.stdout.write(
                                self.style.WARNING(
                                    f"  ⚠ Warning: Expiration update failed: {str(e)}"
                                )
                            )
                    else:
                        # Handle unsuccessful verification
                        code = response_data['data'].get('code') if isinstance(response_data.get('data'), dict) else 'invalid response format'
                        old_status = payment.status
                        payment.status = "ناموفق"
                        payment.save()
                        self.stdout.write(
                            self.style.ERROR(
                                f"\n✗ Payment {payment.id} verification failed!"
                            )
                        )
                        self.stdout.write(f"  Status changed from '{old_status}' to 'ناموفق'")
                        self.stdout.write(f"  Error Code: {code}")
                except ValueError:
                    self.stdout.write(self.style.ERROR(f"\n✗ Invalid JSON response from Zarinpal"))
            else:
                self.stdout.write(self.style.ERROR(f"\n✗ HTTP Error: {response.status_code}"))
                self.stdout.write(f"Response content: {response.text}")

        except requests.exceptions.Timeout:
            self.stdout.write(self.style.ERROR(f"\n✗ Request timeout"))
        except requests.exceptions.ConnectionError:
            self.stdout.write(self.style.ERROR(f"\n✗ Connection error"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n✗ Unexpected error: {str(e)}"))