from collections import OrderedDict

from django.core.validators import RegexValidator, MinLengthValidator, MaxLengthValidator
from drf_writable_nested import WritableNestedModelSerializer
from rest_framework import serializers
from .models import User, TargetInfo, password_length_validator


class TargetInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TargetInfo
        fields = ("age", "country",)

class RegisterUserSerializer(WritableNestedModelSerializer):
    other = TargetInfoSerializer()
    class Meta:
        model = User
        fields = ("name", "surname", "email", "avatar_url", "other", "password", "model_type")
        write_only_fields = ("password", "model_type")

class LoginUserSerializer(serializers.Serializer):
    email = serializers.EmailField(validators=[MinLengthValidator(8), MaxLengthValidator(120)])
    password = serializers.CharField(
        write_only=True,
        validators=[
            MinLengthValidator(8),
            password_length_validator,
            RegexValidator(
                regex=r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
            )
        ],
    )
    class Meta:
        model = User
        fields = ("email", "password",)

class UserSerializer(WritableNestedModelSerializer):
    other = TargetInfoSerializer()

    def to_representation(self, instance):
        result = super().to_representation(instance)
        return OrderedDict(
            [(key, result[key]) for key in result if result[key] is not None]
        )

    class Meta:
        model = User
        fields = ("name", "surname", "email", "avatar_url", "other")
        read_only_fields = ("other",)

class UpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("name", "surname", "avatar_url", "password")

class FeedQueryParamSerializer(serializers.Serializer):
    limit = serializers.IntegerField(required=False)
    offset = serializers.IntegerField(required=False)
    category = serializers.CharField(required=False)
    active = serializers.BooleanField(required=False)
