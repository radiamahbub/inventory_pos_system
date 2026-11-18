from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrCashier


def shop_info():
    return {
        "name": settings.SHOP_NAME,
        "address": settings.SHOP_ADDRESS,
        "phone": settings.SHOP_PHONE,
        "footer": settings.SHOP_RECEIPT_FOOTER,
    }


class ShopInfoSerializer(serializers.Serializer):
    name = serializers.CharField()
    address = serializers.CharField(allow_blank=True)
    phone = serializers.CharField(allow_blank=True)
    footer = serializers.CharField(allow_blank=True)


class ShopInfoView(APIView):
    """Shop name / address / phone / receipt footer (set in the backend environment)."""

    permission_classes = [IsAdminOrCashier]
    serializer_class = ShopInfoSerializer

    @extend_schema(tags=["Shop"], summary="Shop details for invoices and receipts", responses=ShopInfoSerializer)
    def get(self, request):
        return Response(ShopInfoSerializer(shop_info()).data)
