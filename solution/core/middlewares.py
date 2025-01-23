from django.http import JsonResponse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response


class ValidateAuthTokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.headers.get('Authorization')
        if auth_header:
            token = auth_header.split(' ')[-1]
            if not (5 <= len(token) <= 300):
                return JsonResponse({"error": 'Token must be between 5 and 300 characters.'}, status=status.HTTP_400_BAD_REQUEST)

        return self.get_response(request)