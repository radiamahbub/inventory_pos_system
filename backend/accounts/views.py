from django.conf import settings
from django.db.models import ProtectedError
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from config.utils import parse_bool

from .models import Role, User
from .permissions import IsAdminRole
from .serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    LoginResponseSerializer,
    LogoutSerializer,
    RegisterResponseSerializer,
    RegisterSerializer,
    RegistrationStatusSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


@extend_schema(
    tags=["Auth"],
    summary="Login (get JWT access + refresh tokens)",
    responses={200: LoginResponseSerializer},
    examples=[
        OpenApiExample("Login request", value={"username": "admin1", "password": "StrongPass123!"}, request_only=True),
    ],
)
class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(
    tags=["Auth"],
    summary="Logout (blacklist the refresh token)",
    request=LogoutSerializer,
    responses={205: None},
    examples=[OpenApiExample("Logout request", value={"refresh": "<refresh-token>"}, request_only=True)],
)
class LogoutView(APIView):
    # refresh token থাকাই এখানে যথেষ্ট প্রমাণ; access token মেয়াদ শেষ হলেও logout করা যাবে।
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError:
            raise ValidationError({"refresh": "Token is invalid or already blacklisted."})
        return Response(status=status.HTTP_205_RESET_CONTENT)


@extend_schema(
    tags=["Auth"],
    summary="Is self-registration enabled? (public)",
    responses=RegistrationStatusSerializer,
)
class RegistrationStatusView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = RegistrationStatusSerializer

    def get(self, request):
        return Response(
            {
                "enabled": settings.SELF_REGISTRATION_ENABLED,
                "requires_approval": not settings.SELF_REGISTRATION_AUTO_APPROVE,
            }
        )


@extend_schema(
    tags=["Auth"],
    summary="Register a new Cashier account (public)",
    description=(
        "Creates a **Cashier** account (the role cannot be chosen). By default the account is inactive until an "
        "Admin approves it (`SELF_REGISTRATION_AUTO_APPROVE=true` activates it immediately). "
        "Returns 403 when `SELF_REGISTRATION_ENABLED=false`. Rate limited per IP."
    ),
    request=RegisterSerializer,
    responses={201: RegisterResponseSerializer},
    examples=[
        OpenApiExample(
            "Register request",
            value={
                "username": "rahim",
                "first_name": "Rahim",
                "last_name": "Uddin",
                "email": "rahim@example.com",
                "password": "StrongPass123!",
                "confirm_password": "StrongPass123!",
            },
            request_only=True,
        )
    ],
)
class RegisterView(APIView):
    # public endpoint: পুরনো/মেয়াদোত্তীর্ণ token header থাকলেও 401 যেন না আসে
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"
    serializer_class = RegisterSerializer

    def post(self, request):
        if not settings.SELF_REGISTRATION_ENABLED:
            return Response(
                {"detail": "Self-registration is disabled. Please ask an administrator to create your account."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        requires_approval = not user.is_active
        detail = (
            "Account created. An administrator must approve it before you can sign in."
            if requires_approval
            else "Account created. You can sign in now."
        )
        return Response(
            {"detail": detail, "requires_approval": requires_approval, "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Auth"], summary="Current logged-in user", responses=UserSerializer)
class MeView(APIView):
    serializer_class = UserSerializer

    def get(self, request):
        return Response(UserSerializer(request.user).data)


@extend_schema(
    tags=["Auth"],
    summary="Change own password",
    request=ChangePasswordSerializer,
    responses={200: None},
)
class ChangePasswordView(APIView):
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Password changed successfully."})


@extend_schema_view(
    list=extend_schema(
        tags=["Users"],
        parameters=[
            OpenApiParameter("role", str, description="Filter: admin or cashier"),
            OpenApiParameter("is_active", bool, description="Filter by active status"),
        ],
    ),
    retrieve=extend_schema(tags=["Users"]),
    create=extend_schema(tags=["Users"], request=UserCreateSerializer, responses={201: UserCreateSerializer}),
    update=extend_schema(tags=["Users"], request=UserUpdateSerializer, responses=UserUpdateSerializer),
    partial_update=extend_schema(tags=["Users"], request=UserUpdateSerializer, responses=UserUpdateSerializer),
    destroy=extend_schema(tags=["Users"]),
)
class UserViewSet(viewsets.ModelViewSet):
    """User management — Admin only."""

    queryset = User.objects.all().order_by("id")
    permission_classes = [IsAdminRole]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["id", "username", "date_joined"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        role = self.request.query_params.get("role")
        if role:
            if role not in Role.values:
                raise ValidationError({"role": "Must be 'admin' or 'cashier'."})
            qs = qs.filter(role=role)
        is_active = parse_bool(self.request.query_params.get("is_active"), "is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.pk == request.user.pk:
            raise ValidationError({"detail": "You cannot delete your own account."})
        if user.role == Role.ADMIN and not User.objects.filter(
            role=Role.ADMIN, is_active=True
        ).exclude(pk=user.pk).exists():
            raise ValidationError({"detail": "At least one active Admin must remain."})
        try:
            user.delete()
        except ProtectedError:
            raise ValidationError(
                {"detail": "This user has purchase/sale/stock records and cannot be deleted. Deactivate the user instead."}
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
