from collections import OrderedDict

from django.core.validators import MinLengthValidator, RegexValidator, MaxLengthValidator
from rest_framework import serializers
from drf_writable_nested.serializers import WritableNestedModelSerializer

from business.models import Business, Promocode, Target, password_length_validator


class RegisterBusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = ("name", "email", "password", "model_type")
        write_only_fields = ("password", "model_type")

class LoginBusinessSerializer(serializers.Serializer):
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
        model = Business
        fields = ("email", "password",)

class TargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Target
        fields = ['age_from', 'age_until', 'country', 'categories']
        extra_kwargs = {
            'age_from': {'required': False, 'allow_null': True},
            'age_until': {'required': False, 'allow_null': True},
            'country': {'required': False, 'allow_null': True},
            'categories': {'required': False, 'allow_null': True},
        }

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        return instance

    def to_representation(self, instance):
        result = super().to_representation(instance)
        return OrderedDict(
            [(key, result[key]) for key in result if result[key] is not None]
        )

class CreatePromocodeSerializer(WritableNestedModelSerializer):
    target = TargetSerializer(required=True, allow_null=True)

    class Meta:
        model = Promocode
        fields = '__all__'
        read_only_fields = ("uuid", 'company', "created_at")


class PromocodeSerializer(WritableNestedModelSerializer):
    target = TargetSerializer()
    promo_id = serializers.SerializerMethodField()
    company_id = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    active = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    used_count = serializers.SerializerMethodField()

    def get_promo_id(self, obj):
        return obj.uuid

    def get_company_id(self, obj):
        return obj.company.uuid

    def get_company_name(self, obj):
        return obj.company.name

    def get_active(self, obj):
        if obj.active_until and obj.active_from:
            return obj.active_until > obj.active_from # TODO:
        return True

    def get_like_count(self, obj):
        return 0 # TODO:

    def get_used_count(self, obj):
        return 0 # TODO:

    def to_representation(self, instance):
        result = super().to_representation(instance)
        return OrderedDict(
            [(key, result[key]) for key in result if result[key] is not None]
        )

    class Meta:
        model = Promocode
        fields = (
            "description",
            "image_url",
            "target",
            "max_count",
            "active_from",
            "active_until",
            "mode",
            "promo_common",
            "promo_unique",
            "promo_id",
            "company_id",
            "company_name",
            "like_count",
            "used_count",
            "active",
        )
        read_only_fields = (
            "uuid",
            "mode",
            "promo_common",
            "promo_unique",
            "promo_id",
            "company_id",
            "company_name",
            "like_count",
            "used_count",
            "active",
        )

class ListPromocodesQueryParamsSerializer(serializers.Serializer):
    limit = serializers.IntegerField(required=False)
    offset = serializers.IntegerField(required=False)
    sort_by = serializers.ChoiceField(
        choices=["active_from", "active_until", "created_at"],
        default="created_at",
        required=False
    )

