from django.conf import settings
import requests
import json
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import AccountCharge , Payment , UserSettings
from accounts.models import User
from .serializers import PaymentSerializer , AccountChargeSerializer , UserSettingsSerializer
from accounts.serializers import UserSerializer
import time
from rest_framework.authentication import TokenAuthentication, BaseAuthentication
from decimal import Decimal
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from .utils import update_expiration, increase_balance
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from services.models import Service
from random import randint
from django.db import transaction
import logging

logger = logging.getLogger('django')
mainLogger = logging.getLogger('main')

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
# CallbackURL = 'https://app.uzradyab.ir/payment-verify/'  # Important: need to edit for real server.
# CallbackURL = 'http://localhost:3037/payment-verify/'  # Important: need to edit for real server.
# SecondCallbackURL = 'http://localhost:5173/payment-verify/'



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def buy_package(request):
    user = request.user

    mainLogger.info(f"User {user} request to buy a package")

    device_id = request.data.get('deviceId')
    package_id = request.data.get('packageId')

    if not package_id:
        mainLogger.debug(f"package {package_id} not found")
        return Response(
            {"success": False, "message": "سرویس مورد نظر را انتخاب کنید."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not device_id:
        mainLogger.debug(f"device {device_id} not found")
        return Response(
            {"success": False, "message": "دستگاهی برای تمدید انتخاب نشده است."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    base_url = settings.TRACCAR_API_URL
    url = f"{base_url}/devices/{device_id}"

    headers = {
        "Authorization": f"Bearer {user.traccar_token}"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            mainLogger.debug(f"An error occured while retrive device from traccar db")
            return Response({
                "error": "در دریافت دستگاه خطایی رخ داد.",
                "details": response.text
            }, status=response.status_code)

        device = response.json()

        try:
            package = AccountCharge.objects.get(id = package_id)  
        except AccountCharge.DoesNotExist:
            return Response(
                {"success": False, "message": "پکیج مورد نظر یافت نشد."},
                status=status.HTTP_404_BAD_REQUEST
            )

    except Exception as e:
        return Response({"error": str(e)}, status=500)
    
    # Generate unique ref_id
    ref_id = None
    for _ in range(10):
        potential_ref_id = randint(100000, 999999)
        if not Payment.objects.filter(verification_code=potential_ref_id).exists():
            ref_id = potential_ref_id
            break
    
    if not ref_id:
        mainLogger.debug(f"An error occured during creating ref ID")
        return Response(
            {"success": False, "message": "خطا در ایجاد شناسه پرداخت."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    try:
        with transaction.atomic():
            mainLogger.info(f"The new purchase is in progress")
            payment = Payment.objects.create(
                user=request.user if request.user.is_authenticated else None,
                unique_id = device.get("uniqueId"),
                name = device.get("name"),
                device_id_number = device.get("id"),
                phone = user.phone,
                period = package.period,
                amount = package.credit_cost,
                verification_code = ref_id,
                status = 'معلق',
                account_charge = package,
                method = 'credit'
            )
            # Check balance
            if user.credit < package.credit_cost:
                payment.status = "failed"
                payment.save()
                mainLogger.debug(f"Not enough credit")
                return Response(
                    {"success": False, "message": "اعتبار حساب برای این تراکنش کافی نیست."},
                    status=status.HTTP_200_OK
                )
            
            user.credit -= package.credit_cost
            user.save()

            payment.status = 'موفق'
            payment.save()

            update_expiration(payment.device_id_number, payment.account_charge.duration_days)

    except Exception as e:
        mainLogger.error(f"Credit payment failed for user {user.id}: {str(e)}")
        return Response(
            {"success": False, "message": f"{str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return JsonResponse({"success": True, "ref_id": ref_id, "message": "پرداخت با موفقیت انجام شد."})


class ResellersListView(APIView):
    def get(self, request):
        settings = User.objects.filter(is_staff = True, is_superuser = False)
        serializer = UserSerializer(settings, many=True)
        return Response(serializer.data)


class AccountChargeAPIView(APIView):
    def get(self, request):
        print("AccountChargeAPIView GET request received")
        settings = AccountCharge.objects.all()
        serializer = AccountChargeSerializer(settings, many=True)
        print("Serialized data:", serializer.data)
        return Response(serializer.data)

class PayAPIView(APIView):
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]
    def post(self, request):
        mainLogger.info(f"The new payment is in progress")
        data = request.data
        amount = data.get('amount')
        period = data.get('period')
        uniqueId = data.get('uniqueId')
        phone = data.get('phone')
        name = data.get('name')
        device_id_number = data.get('id')
        accountcharges_id = data.get('accountcharges_id')
        payment_type = data.get('payment_type')
        method = data.get('method')
        account_charge = None

        callback_url = f"{settings.CALLBACK_URL}{device_id_number}"

        try:
            if payment_type == 'service':
                service = Service.objects.filter(price=amount).first()
                if not service:
                    mainLogger.debug(f"Invalid service plan")
                    return Response({'error': 'Invalid service plan'}, status=400)

                amount = int(service.price)
                description = service.description
                callback_url = f"{settings.SECOND_CALLBACK_URL}"

                # ✅ ensure these exist, but don't overwrite with 1
                # if not uniqueId or not phone:
                #     mainLogger.debug(f"Missing required fields uniqueId {uniqueId} phone {phone} device_id_number {device_id_number}")
                #     return Response({'error': 'Missing required fields (uniqueId, phone, device_id_number)'}, status=400)


            else:  # account charge
                account_charge = AccountCharge.objects.filter(
                    amount=amount, period=period
                ).first()
                if not account_charge:
                    mainLogger.debug(f"Invalid account charge plan")
                    return Response({'error': 'Invalid account charge plan'}, status=400)

                amount = int(account_charge.amount)  # ✅ always use DB value
                description = account_charge.description
            
            mainLogger.info(f"The new payment create for user {request.user}")
            # Create Payment
            payment = Payment.objects.create(
                user=request.user if request.user.is_authenticated else None,
                unique_id=uniqueId,
                name= request.user.full_name if not name else name,
                device_id_number=device_id_number,
                phone= request.user.phone if not phone else phone,
                period=period,
                amount=amount,
                status="معلق",
                account_charge=account_charge or None,
                method = method or 'gateway'
            )

            # Send to Zarinpal
            response_data = send_request_logic(
                amount,
                description,
                request.user.phone if not phone else phone,
                callback_url,
                payment.id,
            )

            mainLogger.info(f"The response data for payment {payment.id} is: {response_data}")

            if response_data['status']:
                return Response({'url': response_data['url']})
            else:
                mainLogger.debug(f"Payment initiation failed - 'details': {response_data.get('code')}")
                return Response(
                    {'error': 'Payment initiation failed', 'details': response_data.get('code')},
                    status=500
                )

        except Exception as e:
            mainLogger.error(f"Error processing payment: {str(e)}")
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
        logger.info(f"{response_data}")


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

                    logger.info(f"payment: {payment}")
                    logger.info(f"test123123t")
                    # Call utils
                    update_expiration(payment.device_id_number, payment.account_charge.duration_days)

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
            "CallbackURL": settings.CALLBACK_URL,
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
        payment_type = data.get('payment_type')
        traccar_id = data.get('traccar_id')
        service_id = data.get('service_id')

        logger.info("Asdasdasd")
        
        if not authority:
            return Response({'status': False, 'code': 'Authority not provided'})

        try:
            # Retrieve the Payment object based on the authority code
            payment = Payment.objects.get(payment_code=authority)
            amount = int(payment.amount)  # Convert to int for Zarinpal
            
            # Prepare verification data
            verification_data = {
                "merchant_id": settings.MERCHANT,
                "amount": amount,
                "authority": authority,
            }
            headers = {'content-type': 'application/json'}

            # Send verification request to Zarinpal
            response = requests.post(ZP_API_VERIFY, data=json.dumps(verification_data), headers=headers)
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    
                    # Check if verification was successful
                    if (isinstance(response_data.get('data'), dict) and 
                        response_data['data'].get('code') in [100, 101]):
                        
                        # Update payment as successful
                        payment.status = "موفق"
                        payment.verification_code = response_data['data']['ref_id']
                        payment.save()
                        if payment_type == 'service':
                            try:
                                increase_balance(traccar_id, service_id)
                                duration_days = 365
                            except Exception as e:
                                print(f"Warning: Failed to activate service: {e}")

                        else:
                            # Update device expiration using utils
                            try:
                                update_expiration(payment.device_id_number, payment.account_charge.duration_days)
                                duration_days = payment.account_charge.duration_day
                            except Exception as e:
                                print(f"Warning: Failed to update device expiration: {e}")
                        
                        return Response({
                            'status': True,
                            'RefID': response_data['data']['ref_id'],
                            'duration_days': duration_days,
                            'card_pan': response_data['data'].get('card_pan'),
                            'fee': response_data['data'].get('fee'),
                            'code': response_data['data'].get('code'),
                            'message': response_data['data'].get('message'),
                        })
                    else:
                        # Handle failed verification
                        payment.status = "ناموفق"
                        payment.save()
                        
                        error_code = response_data.get('data', {}).get('code', 'verification_failed')
                        return Response({
                            'status': False, 
                            'code': error_code,
                            'message': 'Payment verification failed'
                        })
                        
                except ValueError:
                    return Response({'status': False, 'code': 'invalid_json_response'})
            else:
                return Response({'status': False, 'code': f'http_error_{response.status_code}'})

        except Payment.DoesNotExist:
            return Response({'status': False, 'code': 'payment_not_found'})
        except requests.exceptions.RequestException as e:
            return Response({'status': False, 'code': 'network_error'})


class PaymentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class PaymentListView(generics.ListAPIView):
    queryset = Payment.objects.exclude(method = 'credit').select_related('account_charge').order_by('-timestamp')
    serializer_class = PaymentSerializer
    pagination_class = PaymentPagination

class ResellerPaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    pagination_class = PaymentPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only return payments for the currently logged-in user
        return (
            Payment.objects.filter(user=self.request.user)
            .select_related('account_charge')
            .order_by('-timestamp')
        )
    
class ResellerTransactionsListView(generics.ListAPIView):
    queryset = Payment.objects.filter(method = 'credit').select_related('account_charge').order_by('-timestamp')
    serializer_class = PaymentSerializer
    pagination_class = PaymentPagination