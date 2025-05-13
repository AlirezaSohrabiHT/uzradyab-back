from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token

class LoginView(APIView):
    def post(self, request):
        phone = request.data.get('phone')
        password = request.data.get('password')

        if not phone or not password:
            return Response({'error': 'Phone and password are required.'}, status=400)

        user = authenticate(request, username=phone, password=password)
        if not user:
            return Response({'error': 'Invalid credentials'}, status=401)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key}, status=200)
