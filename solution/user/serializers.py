from collections import OrderedDict

from django.core.validators import RegexValidator, MinLengthValidator, MaxLengthValidator
from drf_writable_nested import WritableNestedModelSerializer
from rest_framework import serializers

from business.models import Promocode, PromocodeAction
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

class PromocodeForUserSerializer(WritableNestedModelSerializer):
    promo_id = serializers.SerializerMethodField()
    company_id = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    active = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    is_activated_by_user = serializers.SerializerMethodField()
    is_liked_by_user = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    def get_promo_id(self, obj):
        return obj.uuid

    def get_company_id(self, obj):
        return obj.company.uuid

    def get_company_name(self, obj):
        return obj.company.name

    def get_active(self, obj): # TODO:
        return True

    def get_like_count(self, obj):
        return PromocodeAction.objects.filter(promocode=obj, type="like").count()

    def get_is_activated_by_user(self, obj):
        return False

    def get_is_liked_by_user(self, obj):
        return False

    def get_comment_count(self, obj):
        return 0

    class Meta:
        model = Promocode
        fields = (
            "promo_id",
            "company_id",
            "company_name",
            "description",
            "image_url",
            "active",
            "is_activated_by_user",
            "like_count",
            "is_liked_by_user",
            "comment_count"
        )

