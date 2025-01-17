from rest_framework import status
from rest_framework.exceptions import APIException
from django.utils.encoding import force_str

class CustomException(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message = 'A server error occurred.'

    def __init__(self, message, field, status_code):
        if status_code is not None: self.status_code = status_code
        if message is not None:
            self.detail = {field: force_str(message)}
        else: self.detail = {'message': force_str(self.default_detail)}
