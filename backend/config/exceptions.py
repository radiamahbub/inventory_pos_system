from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    DRF-এর ডিফল্ট handler-এর সাথে কিছু বাড়তি ক্ষেত্র সামলায়:
    - Django ValidationError  -> 400
    - ProtectedError (অন্য রেকর্ড নির্ভর করছে) -> 409
    - IntegrityError -> 400
    """
    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, "error_dict") else exc.messages
        exc = DRFValidationError(detail=detail)

    response = exception_handler(exc, context)
    if response is not None:
        return response

    if isinstance(exc, ProtectedError):
        return Response(
            {"detail": "This record cannot be deleted because other records depend on it."},
            status=status.HTTP_409_CONFLICT,
        )
    if isinstance(exc, IntegrityError):
        return Response(
            {"detail": "Database integrity error. Please check unique and required fields."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None
