from collections import defaultdict

from django.core.validators import MinLengthValidator, RegexValidator, MaxLengthValidator
from rest_framework import serializers
from drf_writable_nested.serializers import WritableNestedModelSerializer

from business.models import Business, Promocode, Target, password_length_validator, promocode_is_active, \
    PromocodeCommonInstance, PromocodeUniqueInstance, PromocodeUniqueActivation, PromocodeCommonActivation
from core.serializers import ClearNullMixin
from core.utils import validate_country_code


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
        fields = ("email", "password",) # TODO delete


class TargetSerializer(serializers.ModelSerializer, ClearNullMixin):
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

    def validate(self, data):
        if (country := data.get('country')) is not None:
            validate_country_code(country)
        if (category := data.get('categories')) is not None:
            if len(category) > 20:
                raise serializers.ValidationError("len(category) > 20")
        return super().validate(data)


class CreatePromocodeSerializer(WritableNestedModelSerializer):
    target = TargetSerializer(required=True, allow_null=True)
    promo_common = serializers.CharField(required=False, allow_null=True, min_length=5, max_length=30)
    promo_unique = serializers.ListField(
        child=serializers.CharField(min_length=3, max_length=30),
        validators=[MinLengthValidator(1), MaxLengthValidator(5000)],
        required=False
    )

    class Meta:
        model = Promocode
        fields = [
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
        ]

    def validate(self, data):
        mode = data.get('mode')
        promo_common = data.get('promo_common')
        promo_unique = data.get('promo_unique')

        active_from = data.get('active_from')
        active_until = data.get('active_until')
        if active_from and active_until and active_until < active_from:
            raise serializers.ValidationError("active_until < active_from")

        if mode=="COMMON" and promo_unique:
            raise serializers.ValidationError({"promo_unique": "promo_unique не должно быть при mode=COMMON"})

        if mode=="UNIQUE" and promo_common:
            raise serializers.ValidationError({"promo_common": "promo_common не должно быть при mode=UNIQUE"})

        if mode == 'COMMON' and not promo_common:
            raise serializers.ValidationError({"promo_common": "promo_common не может быть пустым, если mode=COMMON."})

        if mode == 'UNIQUE':
            if not promo_unique or len(promo_unique) == 0 or len(promo_unique) > 5000:
                raise serializers.ValidationError(
                    {"promo_unique": "promo_unique не может быть пустым или быть длиннее 5000, если mode=UNIQUE."})
            if data["max_count"] != 1:
                raise serializers.ValidationError(
                    {"max_count": "При mode=UNIQUE max_count может быть только 1."}
                )

        return super().validate(data)

    def create(self, validated_data):
        target_data = validated_data.pop('target')
        promo_common = validated_data.pop('promo_common', None)
        promo_unique_list = validated_data.pop('promo_unique', None)

        if target_data:
            target_instance = Target.objects.create(**target_data)
            validated_data['target'] = target_instance

        promocode_set = Promocode.objects.create(**validated_data)

        if promo_common:
            promocode_set.common_count = promocode_set.max_count
            PromocodeCommonInstance.objects.create(
                promocode=promo_common,
                promocode_set=promocode_set
            )

        if promo_unique_list:
            promocode_set.unique_count = len(promo_unique_list)
            unique_codes = [
                PromocodeUniqueInstance(promocode=code, promocode_set=promocode_set)
                for code in promo_unique_list
            ]
            PromocodeUniqueInstance.objects.bulk_create(unique_codes)

        promocode_set.save()
        return promocode_set


class PromocodeUniqueInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promocode
        fields = ("promocode",)


class PromocodeSerializer(WritableNestedModelSerializer, ClearNullMixin):
    target = TargetSerializer()
    promo_id = serializers.SerializerMethodField()
    company_id = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    active = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    used_count = serializers.SerializerMethodField()
    promo_common = serializers.SerializerMethodField()
    promo_unique = serializers.SerializerMethodField()
    active_from = serializers.SerializerMethodField()
    active_until = serializers.SerializerMethodField()

    def get_promo_id(self, obj):
        return obj.uuid

    def get_company_id(self, obj):
        return obj.company.uuid

    def get_company_name(self, obj):
        return obj.company.name

    def get_active(self, obj):
        return promocode_is_active(obj)

    def get_like_count(self, obj):
        return obj.likes.count()

    def get_promo_common(self, obj):
        if obj.mode == "COMMON":
            return obj.common_code.first().promocode
        return None

    def get_used_count(self, obj):
        return obj.common_activations_count + obj.unique_activations_count

    def get_promo_unique(self, obj):
        if obj.mode == "UNIQUE":
            return list(obj.unique_codes.values_list('promocode', flat=True))
        return None

    def get_active_from(self, obj):
        if obj.active_from:
            return obj.active_from.date()
        return None

    def get_active_until(self, obj):
        if obj.active_until:
            return obj.active_until.date()
        return None

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
    country = serializers.CharField(required=False, min_length=2)
    sort_by = serializers.ChoiceField(
        choices=["active_from", "active_until", "created_at"],
        default="created_at",
        required=False
    )

    def validate_country(self, country):
        validate_country_code(country)


class PromocodeStatSeriazlier(serializers.ModelSerializer):
    activations_count = serializers.SerializerMethodField()
    countries = serializers.SerializerMethodField()

    def get_activations_count(self, obj):
        return obj.common_activations_count + obj.unique_activations_count

    def get_countries(self, promocode):
        if promocode.mode == "UNIQUE":
            activations = PromocodeUniqueActivation.objects.filter(promocode_instanse__promocode_set=promocode)
        else:
            activations = PromocodeCommonActivation.objects.filter(promocode_instanse__promocode_set=promocode)

        country_activation_count = defaultdict(int)

        for activation in activations:
            country = activation.user.other.country
            country_activation_count[country] += 1

        countries_list = [{"country": country, "activations_count": count} for country, count in
                          country_activation_count.items()]

        countries_list.sort(key=lambda x: x["country"].lower())
        return countries_list

    class Meta:
        model = Promocode
        fields = (
            "activations_count",
            "countries"
        )
