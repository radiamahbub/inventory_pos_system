from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Role, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "role", "is_active", "date_joined", "last_login",
        ]
        read_only_fields = fields


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "role", "is_active", "password",
        ]

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=False, style={"input_type": "password"},
        help_text="Optional. Provide to reset the user's password.",
    )

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "role", "is_active", "password",
        ]

    def validate_password(self, value):
        validate_password(value, user=self.instance)
        return value

    def validate(self, attrs):
        instance = self.instance
        request = self.context.get("request")
        new_role = attrs.get("role", instance.role)
        new_active = attrs.get("is_active", instance.is_active)
        demoting = instance.role == Role.ADMIN and (new_role != Role.ADMIN or not new_active)
        if demoting:
            if request and request.user.pk == instance.pk:
                raise serializers.ValidationError(
                    "You cannot remove your own Admin role or deactivate your own account."
                )
            others = User.objects.filter(role=Role.ADMIN, is_active=True).exclude(pk=instance.pk)
            if not others.exists():
                raise serializers.ValidationError("At least one active Admin must remain.")
        return attrs

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate_new_password(self, value):
        validate_password(value, user=self.context["request"].user)
        return value


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Login response-এ token-এর সাথে ইউজারের তথ্যও (role সহ) পাঠায়।"""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["username"] = user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class LoginResponseSerializer(serializers.Serializer):
    """Swagger-এর response schema-র জন্য।"""

    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text="The refresh token to blacklist.")


class RegisterSerializer(serializers.Serializer):
    """Public self-registration। role কখনো client থেকে নেওয়া হয় না — সবসময় Cashier।"""

    username = serializers.CharField(max_length=150)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    password = serializers.CharField(write_only=True, trim_whitespace=False, style={"input_type": "password"})
    confirm_password = serializers.CharField(write_only=True, trim_whitespace=False, style={"input_type": "password"})

    def validate_username(self, value):
        UnicodeUsernameValidator()(value)
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        candidate = User(
            username=attrs["username"],
            email=attrs.get("email", ""),
            first_name=attrs["first_name"],
            last_name=attrs.get("last_name", ""),
        )
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        password = validated_data.pop("password")
        user = User(
            **validated_data,
            role=Role.CASHIER,
            is_active=settings.SELF_REGISTRATION_AUTO_APPROVE,
        )
        user.set_password(password)
        user.save()
        return user


class RegisterResponseSerializer(serializers.Serializer):
    """Swagger response schema।"""

    detail = serializers.CharField()
    requires_approval = serializers.BooleanField()
    user = UserSerializer()


class RegistrationStatusSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    requires_approval = serializers.BooleanField()
