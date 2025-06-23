from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
import requests

User = get_user_model()

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

        return Response({
            'token': token.key,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser
        }, status=200)


class GenerateTraccarTokenView(APIView):
    authentication_classes = [TokenAuthentication]  # Token-based authentication
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    def post(self, request):
        # The authenticated user is now available as `request.user`
        user = request.user
        
        # Extract user input from the request
        username = user.phone  # Use authenticated user's phone (or email if needed)
        password = request.data.get('password')
        
        if not password:
            return Response({"error": "Password is required."}, status=400)

        # Calculate expiration (1 year from now)
        expiration = (timezone.now() + timedelta(days=365)).isoformat()  # ISO 8601 format

        # Traccar API URL
        url = "https://app.uzradyab.ir/api/session/token"

        # Send the POST request to generate the token
        response = requests.post(
            url,
            auth=requests.auth.HTTPBasicAuth(username, password),  # Basic Auth with username and password
            data={'expiration': expiration}  # Set expiration time
        )

        # Check the response status
        if response.status_code == 200:
            try:
                # The token is directly in the response body (raw response)
                token = response.text.strip()  # Get the raw token from the response body
                
                if token:
                    # Save the token in the user's model
                    user.traccar_token = token  # Save the token in the field
                    user.save()
                    return Response({"message": "Token successfully saved for the user."}, status=200)
                else:
                    return Response({"error": "Token not found in response."}, status=400)
            except requests.exceptions.JSONDecodeError:
                return Response({"error": "Response is not valid JSON."}, status=500)
        else:
            return Response({"error": f"Error: {response.status_code}, {response.text}"}, status=response.status_code)

class CheckTraccarTokenView(APIView):
    authentication_classes = [TokenAuthentication]  # Token-based authentication
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    def get(self, request):
        # The authenticated user is now available as `request.user`
        user = request.user
        
        # Check if the user has a Traccar token
        if user.traccar_token:
            return Response({"message": "User has a Traccar token."}, status=200)
        else:
            return Response({"message": "User does not have a Traccar token."}, status=200)