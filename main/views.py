
from django.conf import settings
import requests
import json
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import AccountCharge , Payment , UserSettings
from .serializers import PaymentSerializer , AccountChargeSerializer , UserSettingsSerializer
import time
from decimal import Decimal
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from .utils import update_expiration

#? sandbox merchant 
if settings.SANDBOX:
    ZP_API_REQUEST = f"https://sandbox.zarinpal.com/pg/v4/payment/request.json"
    ZP_API_VERIFY = f"https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
    ZP_API_STARTPAY = f"https://sandbox.zarinpal.com/pg/StartPay/"
else:
    ZP_API_REQUEST = f"https://api.zarinpal.com/pg/v4/payment/request.json"
    ZP_API_VERIFY = f"https://api.zarinpal.com/pg/v4/payment/verify.json"
    ZP_API_STARTPAY = f"https://www.zarinpal.com/pg/StartPay/"



amount = 1000  # Rial / Required
description = "توضیحات مربوط به تراکنش را در این قسمت وارد کنید"  # Required
phone = 'YOUR_PHONE_NUMBER'  # Optional
# CallbackURL = 'https://app.uzradyab.ir/payment-verify/'  # Important: need to edit for real server.\
CallbackURL = 'http://localhost:3037/payment-verify/'  # Important: need to edit for real server.\
class AccountChargeAPIView(APIView):
    def get(self, request):
        print("AccountChargeAPIView GET request received")
        settings = AccountCharge.objects.all()
        serializer = AccountChargeSerializer(settings, many=True)
        print("Serialized data:", serializer.data)
        return Response(serializer.data)

class PayAPIView(APIView):
    def post(self, request):
        data = request.data
        amount = data.get('amount')
        period = data.get('period')
        uniqueId = data.get('uniqueId')
        phone = data.get('phone')
        name = data.get('name')
        device_id_number = data.get('id')
        accountcharges_id = data.get('accountcharges_id')
        
        callback_url = f"{CallbackURL}{device_id_number}"
        
        try:
            # Find account charge settings
            settings = AccountCharge.objects.filter(amount=amount, period=period).latest('timestamp')
            amount = int(settings.amount)
            accountCharge = AccountCharge.objects.get(amount=amount, period=period)
            
            # Create a new Payment entry with status "Pending"
            payment = Payment.objects.create(
                unique_id=uniqueId,
                name=name,
                device_id_number=device_id_number,
                phone=phone,
                period=period,
                amount=amount,
                status="معلق",
                account_charge=accountCharge,
            )

            # Prepare data for Zarinpal payment request
            response_data = send_request_logic(
                amount,
                settings.description,
                phone,
                callback_url,
                payment.id,
            )

            # Send the formatted response back to the frontend
            if response_data['status']:
                return Response({'url': response_data['url']})
            else:
                return Response({'error': 'Payment initiation failed', 'details': response_data.get('code')}, status=500)
                
        except Exception as e:
            return Response({'error': f"Error processing payment: {str(e)}"}, status=500)

def send_request_logic(amount, description, phone, callback_url, unique_id):
    data = {
        "merchant_id": settings.MERCHANT,
        "amount": amount,
        "description": description,
        "callback_url": callback_url,
        "metadata": {"mobile": phone},
    }
    headers = {'content-type': 'application/json'}
    
    try:
        response = requests.post(ZP_API_REQUEST, data=json.dumps(data), headers=headers, timeout=10)
        if 'html' in response.headers.get('Content-Type', '').lower():
            print("Received an HTML error page from Zarinpal.")
            return {'status': False, 'code': 'server_error'}

        response_data = response.json()

        if response.status_code == 200 and response_data.get('data', {}).get('code') == 100:
            authority = response_data['data']['authority']
            Payment.objects.filter(id=unique_id).update(payment_code=authority)
            return {
                'status': True,
                'url': f"{ZP_API_STARTPAY}{authority}/",  # New payment URL
                'authority': authority
            }
        else:
            error_code = response_data.get('errors', [{}])[0].get('code', 'unknown')
            return {'status': False, 'code': error_code}

    except requests.exceptions.Timeout:
        return {'status': False, 'code': 'timeout'}
    except requests.exceptions.ConnectionError:
        return {'status': False, 'code': 'connection_error'}
    except ValueError:
        return {'status': False, 'code': 'invalid_json'}


def Verify(authority):
    print("Verify function called with authority:", authority)
    global amount
    try:
        period = Payment.objects.filter(payment_code=authority).latest('timestamp')
        print("Found payment period:", period)
        
        data = {
            "MerchantID": settings.MERCHANT,
            "Amount": amount,
            "Authority": authority,
        }
        print("Data being sent to ZP_API_VERIFY:", data)
        data = json.dumps(data)
        headers = {'content-type': 'application/json'}

        response = requests.post(ZP_API_VERIFY, data=data, headers=headers)
        print("Response status code:", response.status_code)
        print("Response content:", response.text)
        
        try:
            response_data = response.json()
            print("Parsed response data:", response_data)
        except ValueError:
            print("Error parsing JSON response:", response.text)
            return JsonResponse({'status': False, 'code': 'invalid json response'})

        if response.status_code == 200:
            if response_data['Status'] in [100, 101]:  # Accept both 100 and 101 as successful statuses
                try:
                    payment = Payment.objects.get(payment_code=authority)
                    payment.status = "موفق"
                    payment.verification_code = response_data['RefID']
                    payment.save()

                    # Call utils
                    update_expiration(payment.device_id_number, payment.period)

                    return JsonResponse({'status': True, 'RefID': response_data['RefID'], 'period': period})
                except Payment.DoesNotExist:
                    print("Payment not found for authority:", authority)
                    return JsonResponse({'status': False, 'code': 'Payment not found'})
            else:
                print("Payment verification failed with status:", response_data['Status'])
                payment = Payment.objects.get(payment_code=authority)
                payment.status = "نا موفق"
                payment.save()
                return JsonResponse({'status': False, 'code': str(response_data['Status'])})
        else:
            print("Non-200 status code received for verify:", response.status_code)
            return JsonResponse({'status': False, 'code': response.status_code})

    except requests.exceptions.Timeout:
        print("Request to ZP_API_VERIFY timed out")
        return JsonResponse({'status': False, 'code': 'timeout'})
    except requests.exceptions.ConnectionError:
        print("Connection error to ZP_API_VERIFY")
        return JsonResponse({'status': False, 'code': 'connection error'})

class UserSettingsAPIView(APIView):
    def post(self, request):
        serializer = UserSettingsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    def get(self, request, id):
        try:
            user_settings = UserSettings.objects.get(id=id)
            serializer = UserSettingsSerializer(user_settings)
            return Response(serializer.data)
        except UserSettings.DoesNotExist:
            return Response({'error': 'User settings not found'}, status=404)

class SendRequestAPIView(APIView):
    def get(self, request):
        global amount  # Access the global variable 'amount' inside the method
        
        # Set content length by data
        data = {
            "MerchantID": settings.MERCHANT,
            "Amount": amount,
            "Description": description,
            "Phone": phone,
            "CallbackURL": CallbackURL,
        }
        data = json.dumps(data)
        headers = {'content-type': 'application/json', 'content-length': str(len(data))}
        
        try:
            response = requests.post(ZP_API_REQUEST, data=data, headers=headers, timeout=10)
                    # Log raw response content for debugging
            print("Response status:", response.status_code)
            print("Response content:", response.text)
            response_data = response.json()
            if response.status_code == 200:
                if response_data['Status'] in [100, 101]:  # Accept both 100 and 101 as successful statuses
                    return Response({'status': True, 'url': ZP_API_STARTPAY + str(response_data['Authority']), 'authority': response_data['Authority']})
                else:
                    return Response({'status': False, 'code': str(response_data['Status'])})
            else:
                return Response({'status': False, 'code': response.status_code})

        except requests.exceptions.Timeout:
            return Response({'status': False, 'code': 'timeout'})
        except requests.exceptions.ConnectionError:
            return Response({'status': False, 'code': 'connection error'})








class VerifyAPIView(APIView):
    def post(self, request):
        data = request.data
        authority = data.get('Authority')
        
        if not authority:
            return Response({'status': False, 'code': 'Authority not provided'})

        try:
            # Retrieve the Payment object based on the authority code
            payment = Payment.objects.get(payment_code=authority)
            amount = float(payment.amount)  # Convert Decimal to float
            
            # Prepare verification data with the correct amount
            verification_data = {
                "merchant_id": settings.MERCHANT,
                "amount": amount,
                "authority": authority,
            }
            headers = {'content-type': 'application/json'}

            # Send verification request to Zarinpal
            response = requests.post(ZP_API_VERIFY, data=json.dumps(verification_data), headers=headers)
            print("Data sent for verification:", verification_data)
            print("Response status code:", response.status_code)
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    print("Parsed response data:", response_data)
                    
                    # Verify that 'data' is a dictionary before accessing 'code'
                    if isinstance(response_data.get('data'), dict) and response_data['data'].get('code') in [100, 101]:
                        # Update the payment object with successful verification
                        payment.status = "موفق"  # Set status as successful
                        payment.verification_code = response_data['data']['ref_id']
                        payment.save()
                        
                        duration_days = payment.account_charge.duration_days
                        return Response({
                            'status': True,
                            'RefID': response_data['data']['ref_id'],
                            'duration_days': duration_days,
                            'card_pan': response_data['data'].get('card_pan'),
                            'fee_type': response_data['data'].get('fee_type'),
                            'fee': response_data['data'].get('fee'),
                            'code': response_data['data'].get('code'),
                            'message': response_data['data'].get('message'),
                        })
                    else:
                        # Handle unsuccessful verification codes or unexpected response structure
                        code = response_data['data'].get('code') if isinstance(response_data.get('data'), dict) else 'invalid response format'
                        print("Payment verification failed with code:", code)
                        payment.status = "ناموفق"  # Mark as unsuccessful
                        payment.save()
                        return Response({'status': False, 'code': code})
                except ValueError:
                    print("Error parsing JSON response:", response.text)
                    return Response({'status': False, 'code': 'invalid json response'})
            else:
                # Non-200 response status
                return Response({'status': False, 'code': response.status_code})

        except Payment.DoesNotExist:
            print("Payment not found for authority:", authority)
            return Response({'status': False, 'code': 'Payment not found'})
        except requests.exceptions.Timeout:
            print("Request to ZP_API_VERIFY timed out")
            return Response({'status': False, 'code': 'timeout'})
        except requests.exceptions.ConnectionError:
            print("Connection error to ZP_API_VERIFY")
            return Response({'status': False, 'code': 'connection error'})


class PaymentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class PaymentListView(generics.ListAPIView):
    queryset = Payment.objects.all().select_related('account_charge').order_by('-timestamp')
    serializer_class = PaymentSerializer
    pagination_class = PaymentPagination