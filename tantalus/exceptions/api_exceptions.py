from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException

# taken from documentation here: http://www.django-rest-framework.org/api-guide/exceptions/#custom-exception-handling
# and http://masnun.com/2015/11/06/django-rest-framework-custom-exception-handler.html
# def custom_exception_handler(exc, context):
#     # Call REST framework's default exception handler first,
#     # to get the standard error response.
#     response = exception_handler(exc, context)
#
#     # Now add the HTTP status code to the response.
#     if response is not None:
#         response.data['status_code'] = response.status_code
#
#     return response

