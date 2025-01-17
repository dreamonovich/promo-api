import copy

from django.http import QueryDict
from rest_framework import serializers
from drf_writable_nested.serializers import WritableNestedModelSerializer

from business.models import Business, Promocode, Target


class CreateBusinessSerializer(serializers.ModelSerializer):
    def validate(self, data):
        password = data.get('password')
        if password and len(password) > 60:
            raise serializers.ValidationError({"password": "Пароль не должен превышать 60 символов."})
        return data

    class Meta:
        model = Business
        fields = ("name", "email", "password")

class LoginBusinessSerializer(serializers.Serializer):
    def validate(self, data):
        password = data.get('password')
        if password and len(password) > 60:
            raise serializers.ValidationError({"password": "Пароль не должен превышать 60 символов."})
        return data

    class Meta:
        model = Business
        fields = ("email", "password",)

class TargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Target
        fields = ['age_from', 'age_until', 'country', 'categories']

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data) # NO PARTIAL UPDATE
        return instance

class CreatePromocodeSerializer(WritableNestedModelSerializer):
    target = TargetSerializer()

    class Meta:
        model = Promocode
        fields = (
            "uuid",
            "description",
            "image_url",
            "target",
            "max_count",
            "active_from",
            "active_until",
            "mode",
            "promo_common",
            "promo_unique",
        )
        read_only_fields = ("uuid",)

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
        return obj.active_until > obj.active_from

    def get_like_count(self, obj):
        return 0

    def get_used_count(self, obj):
        return 0

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

