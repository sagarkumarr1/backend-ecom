from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Saari errors ek clean JSON format mein aayengi.
    Stack trace kabhi bhi client ko nahi milega.
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_detail = response.data

        # Single string error
        if isinstance(error_detail.get('detail'), str):
            message = error_detail['detail']
        # List of errors
        elif isinstance(error_detail, list):
            message = error_detail[0] if error_detail else "Error"
        # Dict of field errors
        elif isinstance(error_detail, dict):
            first_key = next(iter(error_detail), None)
            if first_key:
                val = error_detail[first_key]
                message = val[0] if isinstance(val, list) else str(val)
            else:
                message = "Kuch galat hua."
        else:
            message = "Kuch galat hua."

        response.data = {
            'success':     False,
            'status_code': response.status_code,
            'message':     str(message),
            'errors':      error_detail,
        }

    return response
