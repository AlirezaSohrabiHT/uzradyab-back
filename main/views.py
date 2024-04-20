# from django.conf import settings
# import requests
# import json
# from django.http import JsonResponse
# from rest_framework import status
# from rest_framework.response import Response
# from rest_framework.views import APIView
# from .models import AccountCharge , Payment
# from .serializers import AccountChargeSerializer

# #? sandbox merchant 
# if settings.SANDBOX:
#     sandbox = 'sandbox'
# else:
#     sandbox = 'www'


# ZP_API_REQUEST = f"https://{sandbox}.zarinpal.com/pg/rest/WebGate/PaymentRequest.json"
# ZP_API_VERIFY = f"https://{sandbox}.zarinpal.com/pg/rest/WebGate/PaymentVerification.json"
# ZP_API_STARTPAY = f"https://{sandbox}.zarinpal.com/pg/StartPay/"

# amount = 1000  # Rial / Required
# description = "توضیحات مربوط به تراکنش را در این قسمت وارد کنید"  # Required
# phone = 'YOUR_PHONE_NUMBER'  # Optional
# # Important: need to edit for realy server.
# CallbackURL = 'http://127.0.0.1:8000/verify/'

# from django.http import JsonResponse


# class AccountChargeAPIView(APIView):
#     def get(self, request):
#         # Retrieve all Setting objects
#         settings = AccountCharge.objects.all()
        
#         # Serialize the queryset
#         serializer = AccountChargeSerializer(settings, many=True)
        
#         # Return serialized data as JSON response
#         return Response(serializer.data)



# class PayAPIView(APIView):
#     def post(self, request):
#         # Retrieve data from the request body
#         data = request.data
#         amount = data.get('amount')
#         period = data.get('period')
#         uniqueId =  data.get('uniqueId')
#         phone =  data.get('phone')
#         name = data.get('name')
#         id = data.get('id')
#         if not data:
#             return Response({'error': 'No data provided'}, status=400)

#         # Save the data as a dictionary
#         try:
#             # Assuming you want to save the received data as is
#             settings = AccountCharge.objects.filter(amount=amount, period=period).latest('timestamp')
#             amount = int(settings.amount)

#             payment = Payment.objects.create(
#                 unique_id=uniqueId,
#                 name=name,
#                 id_number=id,
#                 phone=phone,
#                 period=period,
#                 amount=amount,
#                 status="معلق",  # Set initial status as pending or pending approval
#             )
#             request.session['payment_id'] = payment.id

#             response_data = send_request_logic(
#                 amount,
#                 settings.description,
#                 'YOUR_PHONE_NUMBER',
#                 'http://127.0.0.1:8000/verify/',
#             )

#             if response_data.get('status'):
#                 # Payment request successful
#                 return Response({'message': 'Payment request successful'})
#             else:
#                 # Payment request failed
#                 return Response({'error': 'Payment request failed'}, status=status.HTTP_400_BAD_REQUEST)

#         except Exception as e:
#             return Response({'error': f"Error processing payment: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




# def send_request_logic(amount, description, phone, CallbackURL):
#     data = {
#         "MerchantID": settings.MERCHANT,
#         "Amount": amount,
#         "Description": description,
#         "Phone": phone,
#         "CallbackURL": CallbackURL,
#     }
#     data = json.dumps(data)
#     headers = {'content-type': 'application/json', 'content-length': str(len(data))}
#     try:
#         response = requests.post(ZP_API_REQUEST, data=data, headers=headers, timeout=10)
#         response_data = response.json()
#         if response.status_code == 200:
#             if response_data.get('Status') == 100:  # Using .get() to avoid KeyError
#                 return {'status': True, 'url': ZP_API_STARTPAY + str(response_data['Authority']), 'authority': response_data['Authority']}
#             else:
#                 return {'status': False, 'code': str(response_data.get('Status', ''))}
#         else:
#             return {'status': False, 'code': response.status_code}

#     except requests.exceptions.Timeout:
#         return {'status': False, 'code': 'timeout'}
#     except requests.exceptions.ConnectionError:
#         return {'status': False, 'code': 'connection error'}



# class SendRequestAPIView(APIView):
#     def get(self, request):
#         amount = 1000  # Rial / Required
#         description = "توضیحات مربوط به تراکنش را در این قسمت وارد کنید"  # Required
#         phone = 'YOUR_PHONE_NUMBER'  # Optional
#         CallbackURL = 'http://127.0.0.1:8000/verify/'  # Important: need to edit for real server.
        
#         data = {
#             "MerchantID": settings.MERCHANT,
#             "Amount": amount,
#             "Description": description,
#             "Phone": phone,
#             "CallbackURL": CallbackURL,
#         }
#         data = json.dumps(data)

#         # set content length by data
#         headers = {'content-type': 'application/json', 'content-length': str(len(data))}
#         try:
#             response = requests.post(ZP_API_REQUEST, data=data, headers=headers, timeout=10)
#             response_data = response.json()
#             if response.status_code == 200:
#                 if response_data['Status'] == 100:
#                     return Response({'status': True, 'url': ZP_API_STARTPAY + str(response_data['Authority']), 'authority': response_data['Authority']})
#                 else:
#                     return Response({'status': False, 'code': str(response_data['Status'])})
#             else:
#                 return Response({'status': False, 'code': response.status_code})

#         except requests.exceptions.Timeout:
#             return Response({'status': False, 'code': 'timeout'})
#         except requests.exceptions.ConnectionError:
#             return Response({'status': False, 'code': 'connection error'})

# class VerifyAPIView(APIView):
#     def get(self, request):
#         # Retrieve payment ID from session
#         payment_id = request.session.get('payment_id')
        
#         if not payment_id:
#             return Response({'error': 'Payment ID not found in session'}, status=status.HTTP_400_BAD_REQUEST)

#         # Retrieve payment object
#         try:
#             payment = Payment.objects.get(pk=payment_id)
#         except Payment.DoesNotExist:
#             return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

#         # Perform payment verification
#         amount = 1000  # Rial / Required (you may adjust this)
#         authority = request.GET.get('Authority')
#         if not authority:
#             return Response({'status': False, 'code': 'Authority not provided'})
        
#         data = {
#             "MerchantID": settings.MERCHANT,
#             "Amount": amount,
#             "Authority": authority,
#         }
#         data = json.dumps(data)
#         headers = {'content-type': 'application/json', 'content-length': str(len(data))}
#         try:
#             response = requests.post(ZP_API_VERIFY, data=data, headers=headers)
#             response_data = response.json()
#             if response.status_code == 200:
#                 if response_data['Status'] == 100:
#                     # Payment successful, update payment status
#                     payment.status = "موفق"  # Set status as successful
#                     payment.save()
#                     return Response({'status': True, 'RefID': response_data['RefID']})
#                 else:
#                     # Payment unsuccessful, update payment status
#                     payment.status = "ناموفق"  # Set status as unsuccessful
#                     payment.save()
#                     return Response({'status': False, 'code': str(response_data['Status'])})
#             else:
#                 return Response({'status': False, 'code': response.status_code})

#         except requests.exceptions.Timeout:
#             return Response({'status': False, 'code': 'timeout'})
#         except requests.exceptions.ConnectionError:
#             return Response({'status': False, 'code': 'connection error'})


from django.conf import settings
import requests
import json
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import AccountCharge , Payment
from .serializers import AccountChargeSerializer
import time

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
CallbackURL = 'http://localhost:3000/settings/device/'  # Important: need to edit for real server.

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
        global amount  # Access the global variable 'amount' inside the method
        amount = data.get('amount')
        period = data.get('period')
        uniqueId = data.get('uniqueId')
        phone = data.get('phone')
        name = data.get('name')
        id_number = data.get('id')
        
        # Check if any data is provided
        if not data:
            return Response({'error': 'No data provided'}, status=400)
        
        try:
            # Assuming you want to save the received data as is
            settings = AccountCharge.objects.filter(amount=amount, period=period).latest('timestamp')
            amount = int(settings.amount)
            payment = Payment.objects.create(
                unique_id=uniqueId,
                name=name,
                id_number=id_number,
                phone=phone,
                period=period,
                amount=amount,
                status="معلق",  # Set initial status as pending or pending approval
            )
            response_data = send_request_logic(
                amount,
                settings.description,
                'YOUR_PHONE_NUMBER',
                'http://localhost:3000/settings/device/',
                payment.id,
            )

            return Response(response_data)  # Return the response from send_request_logic
        except Exception as e:
            return Response({'error': f"Error saving data: {e}"}, status=500)

def send_request_logic(amount, description, phone, CallbackURL, uniqueId):
    print(uniqueId)
    data = {
        "MerchantID": settings.MERCHANT,
        "Amount": amount,
        "Description": description,
        "Phone": phone,
        "CallbackURL": CallbackURL,
    }
    data = json.dumps(data)
    headers = {'content-type': 'application/json'}
    
    try:
        response = requests.post(ZP_API_REQUEST, data=data, headers=headers, timeout=10)
        response_data = response.json()
        
        if response.status_code == 200:
            if response_data.get('Status') == 100:
                # Update payment code based on uniqueId
                Payment.objects.filter(id=uniqueId).update(payment_code=response_data.get('Authority'))
                start_time = time.time()
                verification_response = Verify(response_data.get('Authority'))
                return {'status': True, 'url': ZP_API_STARTPAY + str(response_data.get('Authority')), 'authority': response_data.get('Authority')}
            else:
                return {'status': False, 'code': str(response_data.get('Status'))}
        else:
            return {'status': False, 'code': response.status_code}

    except requests.exceptions.Timeout:
        return {'status': False, 'code': 'timeout'}
    except requests.exceptions.ConnectionError:
        return {'status': False, 'code': 'connection error'}

def Verify(authority):
    global amount  # Access the global variable 'amount' inside the method
    authority = authority
    print(authority)
    if not authority:
        return JsonResponse({'status': False, 'code': 'Authority not provided'})

    data = {
        "MerchantID": settings.MERCHANT,
        "Amount": amount,
        "Authority": authority,
    }
    data = json.dumps(data)
    headers = {'content-type': 'application/json'}

    try:
        response = requests.post(ZP_API_VERIFY, data=data, headers=headers)
        print(data)
        if response.status_code == 200:
            response_data = response.json()
            print(response_data)
            if response_data['Status'] == 100:
                # Find the payment object and update status
                try:
                    payment = Payment.objects.get(payment_code=authority)
                    payment.status = "موفق"  # Set status as successful
                    payment.verification_code = response_data['RefID']
                    payment.save()
                    return JsonResponse({'status': True, 'RefID': response_data['RefID']})
                except Payment.DoesNotExist:
                    print(authority)
                    return JsonResponse({'status': False, 'code': 'Payment not found'})
            else:
                print(authority)
                payment = Payment.objects.get(payment_code=authority)
                payment.status = "نا موفق"  # Set status as successful
                payment.save()
                return JsonResponse({'status': False, 'code': str(response_data['Status'])})
        else:
            return JsonResponse({'status': False, 'code': response.status_code})

    except requests.exceptions.Timeout:
        return JsonResponse({'status': False, 'code': 'timeout'})
    except requests.exceptions.ConnectionError:
        return JsonResponse({'status': False, 'code': 'connection error'})



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
        global amount  # Access the global variable 'amount' inside the method
        
        amount = 5000  # Rial / Required (you may adjust this)
        authority = request.GET.get('Authority')
        if not authority:
            return Response({'status': False, 'code': 'Authority not provided'})

        data = {
            "MerchantID": settings.MERCHANT,
            "Amount": amount,
            "Authority": authority,
        }
        data = json.dumps(data)
        headers = {'content-type': 'application/json'}

        try:
            response = requests.post(ZP_API_VERIFY, data=data, headers=headers)
            print(data)
            if response.status_code == 200:
                response_data = response.json()
                if response_data['Status'] == 100:
                    # Find the payment object and update status
                    try:
                        payment = Payment.objects.get(payment_code=authority)
                        payment.status = "موفق"  # Set status as successful
                        payment.verification_code = response_data['RefID']
                        payment.save()
                        return Response({'status': True, 'RefID': response_data['RefID']})
                    except Payment.DoesNotExist:
                        print(authority)
                        return Response({'status': False, 'code': 'Payment not found'})
                else:
                    print(authority)
                    payment = Payment.objects.get(payment_code=authority)
                    payment.status = "نا موفق"  # Set status as successful
                    payment.save()
                    return Response({'status': False, 'code': str(response_data['Status'])})
            else:
                return Response({'status': False, 'code': response.status_code})

        except requests.exceptions.Timeout:
            return Response({'status': False, 'code': 'timeout'})
        except requests.exceptions.ConnectionError:
            return Response({'status': False, 'code': 'connection error'})





# amount = 1000  # Rial / Required
# description = "توضیحات مربوط به تراکنش را در این قسمت وارد کنید"  # Required
# phone = 'YOUR_PHONE_NUMBER'  # Optional
# # Important: need to edit for realy server.
# CallbackURL = 'http://127.0.0.1:8000/verify/'

# from django.http import JsonResponse


# class AccountChargeAPIView(APIView):
#     def get(self, request):
#         # Retrieve all Setting objects
#         settings = AccountCharge.objects.all()

#         # Serialize the queryset
#         serializer = AccountChargeSerializer(settings, many=True)

#         # Return serialized data as JSON response
#         return Response(serializer.data)



# class PayAPIView(APIView):
#     def post(self, request):
#         # Retrieve data from the request body
#         data = request.data
#         amount = data.get('amount')
#         period = data.get('period')
#         uniqueId = data.get('uniqueId')
#         phone = data.get('phone')
#         name = data.get('name')
#         id_number = data.get('id')
        
#         # Check if any data is provided


#         if not data:
#             return Response({'error': 'No data provided'}, status=400)
#         try:
# #             # Assuming you want to save the received data as is
#             settings = AccountCharge.objects.filter(amount=amount, period=period).latest('timestamp')
#             amount = int(settings.amount)
#             payment = Payment.objects.create(
#                 unique_id=uniqueId,
#                 name=name,
#                 id_number=id_number,
#                 phone=phone,
#                 period=period,
#                 amount=amount,
#                 status="معلق",  # Set initial status as pending or pending approval
#             )
#             response_data = send_request_logic(
#                 amount,
#                 settings.description,
#                 'YOUR_PHONE_NUMBER',
#                 'http://127.0.0.1:8000/verify/',
#                 payment.id,
#             )

#             return Response(response_data)  # Return the response from send_request_logic
#         except Exception as e:
#             return Response({'error': f"Error saving data: {e}"}, status=500)

#             # saved_data = data

#             # response_data = send_request_logic(1000, "توضیحات مربوط به تراکنش را در این قسمت وارد کنید", 'YOUR_PHONE_NUMBER', 'http://127.0.0.1:8000/verify/')

#             return Response(response_data)  # Return the response from send_request_logic
#         except Exception as e:
#             return Response({'error': f"Error saving data: {e}"}, status=500)



# def send_request_logic(amount, description, phone, CallbackURL, uniqueId):
#     print(uniqueId)
#     data = {
#         "MerchantID": settings.MERCHANT,
#         "Amount": amount,
#         "Description": description,
#         "Phone": phone,
#         "CallbackURL": CallbackURL,
#     }
#     data = json.dumps(data)
#     headers = {'content-type': 'application/json'}
    
#     try:
#         response = requests.post(ZP_API_REQUEST, data=data, headers=headers, timeout=10)
#         response_data = response.json()
        
#         if response.status_code == 200:
#             if response_data.get('Status') == 100:
#                 # Update payment code based on uniqueId
#                 Payment.objects.filter(id=uniqueId).update(payment_code=response_data.get('Authority'))
#                 return {'status': True, 'url': ZP_API_STARTPAY + str(response_data.get('Authority')), 'authority': response_data.get('Authority')}
#             else:
#                 return {'status': False, 'code': str(response_data.get('Status'))}
#         else:
#             return {'status': False, 'code': response.status_code}

#     except requests.exceptions.Timeout:
#         return {'status': False, 'code': 'timeout'}
#     except requests.exceptions.ConnectionError:
#         return {'status': False, 'code': 'connection error'}



# class SendRequestAPIView(APIView):
#     def get(self, request):
#         amount = 1000  # Rial / Required
#         description = "توضیحات مربوط به تراکنش را در این قسمت وارد کنید"  # Required
#         phone = 'YOUR_PHONE_NUMBER'  # Optional
#         CallbackURL = 'http://127.0.0.1:8000/verify/'  # Important: need to edit for real server.

#         data = {
#             "MerchantID": settings.MERCHANT,
#             "Amount": amount,
#             "Description": description,
#             "Phone": phone,
#             "CallbackURL": CallbackURL,
#         }
#         data = json.dumps(data)
#         # set content length by data
#         headers = {'content-type': 'application/json', 'content-length': str(len(data))}
#         try:
#             response = requests.post(ZP_API_REQUEST, data=data, headers=headers, timeout=10)
#             response_data = response.json()
#             if response.status_code == 200:
#                 if response_data['Status'] == 100:
#                     return Response({'status': True, 'url': ZP_API_STARTPAY + str(response_data['Authority']), 'authority': response_data['Authority']})
#                 else:
#                     return Response({'status': False, 'code': str(response_data['Status'])})
#             else:
#                 return Response({'status': False, 'code': response.status_code})

#         except requests.exceptions.Timeout:
#             return Response({'status': False, 'code': 'timeout'})
#         except requests.exceptions.ConnectionError:
#             return Response({'status': False, 'code': 'connection error'})

# class VerifyAPIView(APIView):
#     def get(self, request):
#         amount = 5000  # Rial / Required (you may adjust this)
#         authority = request.GET.get('Authority')
#         if not authority:
#             return Response({'status': False, 'code': 'Authority not provided'})

#         data = {
#             "MerchantID": settings.MERCHANT,
#             "Amount": amount,
#             "Authority": authority,
#         }
#         data = json.dumps(data)
#         headers = {'content-type': 'application/json'}

#         try:
#             response = requests.post(ZP_API_VERIFY, data=data, headers=headers)
#             print(data)
#             if response.status_code == 200:
#                 response_data = response.json()
#                 if response_data['Status'] == 100:
#                     # Find the payment object and update status
#                     try:
#                         payment = Payment.objects.get(payment_code=authority)
#                         payment.status = "موفق"  # Set status as successful
#                         payment.verification_code = response_data['RefID']
#                         payment.save()
#                         return Response({'status': True, 'RefID': response_data['RefID']})
#                     except Payment.DoesNotExist:
#                         print(authority)
#                         return Response({'status': False, 'code': 'Payment not found'})
#                 else:
#                     print(authority)
#                     payment = Payment.objects.get(payment_code=authority)
#                     payment.status = "نا موفق"  # Set status as successful
#                     payment.save()
#                     return Response({'status': False, 'code': str(response_data['Status'])})
#             else:
#                 return Response({'status': False, 'code': response.status_code})

#         except requests.exceptions.Timeout:
#             return Response({'status': False, 'code': 'timeout'})
#         except requests.exceptions.ConnectionError:
#             return Response({'status': False, 'code': 'connection error'})