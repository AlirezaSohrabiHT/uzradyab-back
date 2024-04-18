from django.conf import settings
import requests
import json
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import AccountCharge
from .serializers import AccountChargeSerializer

#? sandbox merchant 
if settings.SANDBOX:
    sandbox = 'sandbox'
else:
    sandbox = 'www'


ZP_API_REQUEST = f"https://{sandbox}.zarinpal.com/pg/rest/WebGate/PaymentRequest.json"
ZP_API_VERIFY = f"https://{sandbox}.zarinpal.com/pg/rest/WebGate/PaymentVerification.json"
ZP_API_STARTPAY = f"https://{sandbox}.zarinpal.com/pg/StartPay/"

amount = 1000  # Rial / Required
description = "توضیحات مربوط به تراکنش را در این قسمت وارد کنید"  # Required
phone = 'YOUR_PHONE_NUMBER'  # Optional
# Important: need to edit for realy server.
CallbackURL = 'http://127.0.0.1:8000/verify/'

from django.http import JsonResponse


class AccountChargeAPIView(APIView):
    def get(self, request):
        # Retrieve all Setting objects
        settings = AccountCharge.objects.all()
        
        # Serialize the queryset
        serializer = AccountChargeSerializer(settings, many=True)
        
        # Return serialized data as JSON response
        return Response(serializer.data)



class PayAPIView(APIView):
    def post(self, request):
        # Retrieve data from the request body
        data = request.data
        amount = data.get('amount')
        period = data.get('period')
        # Check if any data is provided
        if not data:
            return Response({'error': 'No data provided'}, status=400)

        # Save the data as a dictionary
        try:
            # Assuming you want to save the received data as is
            settings = AccountCharge.objects.filter(amount=amount, period=period).latest('timestamp')

            response_data = send_request_logic(
                str(settings.amount),
                settings.description,
                'YOUR_PHONE_NUMBER',
                'http://127.0.0.1:8000/verify/'
            )

            # saved_data = data

            # response_data = send_request_logic(1000, "توضیحات مربوط به تراکنش را در این قسمت وارد کنید", 'YOUR_PHONE_NUMBER', 'http://127.0.0.1:8000/verify/')
            
            return Response(response_data)  # Return the response from send_request_logic
        except Exception as e:
            return Response({'error': f"Error saving data: {e}"}, status=500)



def send_request_logic(amount , description , phone , CallbackURL ):
    data = {
        "MerchantID": settings.MERCHANT,
        "Amount": amount,
        "Description": description,
        "Phone": phone,
        "CallbackURL": CallbackURL,
    }
    data = json.dumps(data)
    # set content length by data
    headers = {'content-type': 'application/json', 'content-length': str(len(data))}
    try:
        response = requests.post(ZP_API_REQUEST, data=data, headers=headers, timeout=10)
        response_data = response.json()
        if response.status_code == 200:
            if response_data['Status'] == 100:
                return {'status': True, 'url': ZP_API_STARTPAY + str(response_data['Authority']), 'authority': response_data['Authority']}
            else:
                return {'status': False, 'code': str(response_data['Status'])}
        else:
            return {'status': False, 'code': response.status_code}

    except requests.exceptions.Timeout:
        return {'status': False, 'code': 'timeout'}
    except requests.exceptions.ConnectionError:
        return {'status': False, 'code': 'connection error'}


# class SendRequestAPIView(APIView):
    def get(self, request):
        amount = 1000  # Rial / Required
        description = "توضیحات مربوط به تراکنش را در این قسمت وارد کنید"  # Required
        phone = 'YOUR_PHONE_NUMBER'  # Optional
        CallbackURL = 'http://127.0.0.1:8000/verify/'  # Important: need to edit for real server.
        
        data = {
            "MerchantID": settings.MERCHANT,
            "Amount": amount,
            "Description": description,
            "Phone": phone,
            "CallbackURL": CallbackURL,
        }
        data = json.dumps(data)
        # set content length by data
        headers = {'content-type': 'application/json', 'content-length': str(len(data))}
        try:
            response = requests.post(ZP_API_REQUEST, data=data, headers=headers, timeout=10)
            response_data = response.json()
            if response.status_code == 200:
                if response_data['Status'] == 100:
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
    def get(self, request):
        amount = 1000  # Rial / Required (you may adjust this)
        authority = request.GET.get('Authority')
        if not authority:
            return Response({'status': False, 'code': 'Authority not provided'})
        
        data = {
            "MerchantID": settings.MERCHANT,
            "Amount": amount,
            "Authority": authority,
        }
        data = json.dumps(data)
        # set content length by data
        headers = {'content-type': 'application/json', 'content-length': str(len(data))}
        try:
            response = requests.post(ZP_API_VERIFY, data=data, headers=headers)
            response_data = response.json()
            if response.status_code == 200:
                if response_data['Status'] == 100:
                    return Response({'status': True, 'RefID': response_data['RefID']})
                else:
                    return Response({'status': False, 'code': str(response_data['Status'])})
            else:
                return Response({'status': False, 'code': response.status_code})

        except requests.exceptions.Timeout:
            return Response({'status': False, 'code': 'timeout'})
        except requests.exceptions.ConnectionError:
            return Response({'status': False, 'code': 'connection error'})