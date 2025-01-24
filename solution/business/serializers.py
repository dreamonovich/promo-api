from collections import defaultdict

from django.core.validators import MinLengthValidator, RegexValidator, MaxLengthValidator, MinValueValidator, \
    MaxValueValidator
from rest_framework import serializers
from drf_writable_nested.serializers import WritableNestedModelSerializer
from rest_framework.exceptions import ValidationError

from business.models import Business, Promocode, Target, password_length_validator, promocode_is_active, \
    PromocodeCommonInstance, PromocodeUniqueInstance, PromocodeUniqueActivation, PromocodeCommonActivation
from core.utils import clean_country
from core.serializers import ClearNullMixin, StrictCharField, StrictIntegerField, StrictURLField
from core.utils import validate_country_code


class RegisterBusinessSerializer(serializers.ModelSerializer):
    name = StrictCharField(
        validators=[MinLengthValidator(5)],
        max_length=50,
    )
    class Meta:
        model = Business
        fields = ("name", "email", "password", "model_type")
        write_only_fields = ("password", "model_type")


class LoginBusinessSerializer(serializers.Serializer):
    email = serializers.EmailField(validators=[MinLengthValidator(8), MaxLengthValidator(120)])
    password = StrictCharField(
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
        fields = ("email", "password",) # delete maybe


class TargetSerializer(serializers.ModelSerializer, ClearNullMixin):
    age_from = StrictIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        required=False,
        allow_null=True,
    )
    age_until = StrictIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        required=False,
        allow_null=True,
    )
    categories = serializers.ListField(
        child=StrictCharField(validators=[MinLengthValidator(2), MaxLengthValidator(20)], max_length=20),
        max_length=20,
        required=False,
        allow_null=True,
    )
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
    promo_common = StrictCharField(required=False, allow_null=True, min_length=5, max_length=30)
    promo_unique = serializers.ListField(
        child=StrictCharField(min_length=3, max_length=30),
        validators=[MinLengthValidator(1), MaxLengthValidator(5000)],
        required=False
    )
    description = StrictCharField(
        max_length=300,
        validators=[
            MinLengthValidator(10),
            MaxLengthValidator(300),
        ],
    )
    image_url = StrictURLField(
        max_length=350,
        required=False,
        allow_null=True,
        validators=[MinLengthValidator(1), MaxLengthValidator(350)]
    )
    max_count = StrictIntegerField(validators=[MinValueValidator(0), MaxValueValidator(100000000)])

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
        if active_from is not None and active_until is not None and active_until < active_from:
            raise serializers.ValidationError("active_until < active_from")

        if mode=="COMMON" and promo_unique is not None:
            raise serializers.ValidationError({"promo_unique": "promo_unique не должно быть при mode=COMMON"})

        if mode=="UNIQUE" and promo_common is not None:
            raise serializers.ValidationError({"promo_common": "promo_common не должно быть при mode=UNIQUE"})

        if mode == 'COMMON' and not promo_common is not None:
            raise serializers.ValidationError({"promo_common": "promo_common не может быть пустым, если mode=COMMON."})

        if mode == 'UNIQUE':
            if promo_unique is None or len(promo_unique) == 0 or len(promo_unique) > 5000:
                raise serializers.ValidationError(
                    {"promo_unique": "promo_unique не может быть пустым или быть длиннее 5000, если mode=UNIQUE."})
            if data["max_count"] != 1:
                raise serializers.ValidationError(
                    {"max_count": "При mode=UNIQUE max_count может быть только 1."}
                )
        if data.get("image_url") == '':
            raise ValidationError("image_url must not be empty")
        return super().validate(data)

    def create(self, validated_data):
        target_data = validated_data.pop('target')
        promo_common = validated_data.pop('promo_common', None)
        promo_unique_list = validated_data.pop('promo_unique', None)

        if target_data is not None:
            target_instance = Target.objects.create(**target_data)
            validated_data['target'] = target_instance

        promocode_set = Promocode.objects.create(**validated_data)

        if promo_common is not None:
            promocode_set.common_count = promocode_set.max_count
            PromocodeCommonInstance.objects.create(
                promocode=promo_common,
                promocode_set=promocode_set
            )

        if promo_unique_list is not None:
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
    active_until = serializers.DateTimeField(format="%Y-%m-%d", input_formats=["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"], required=False, allow_null=True)
    active_from = serializers.DateTimeField(format="%Y-%m-%d", input_formats=["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"],
                                             required=False, allow_null=True)
    description = StrictCharField(
        max_length=300,
        validators=[
            MinLengthValidator(10),
            MaxLengthValidator(300),
        ],
    )
    image_url = StrictURLField(
        max_length=350,
        required=False,
        allow_null=True,
        validators=[MinLengthValidator(1), MaxLengthValidator(350)]
    )
    max_count = StrictIntegerField(validators=[MinValueValidator(0), MaxValueValidator(100000000)])

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

    def get_active_until(self, obj):
        return obj.active_until.date() if obj.active_until else None

    def get_active_from(self, obj):
        return obj.active_from.date() if obj.active_from else None

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

    def update(self, instance, validated_data):
        if 'active_until' in validated_data:
            instance.active_until = validated_data['active_until']
        if 'active_from' in validated_data:
            instance.active_from = validated_data['active_from']
        instance.save()
        return super().update(instance, validated_data)


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
        validate_country_code(*clean_country(country))


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
            country_activation_count[country.lower()] += 1

        countries_list = [{"country": country.lower(), "activations_count": count} for country, count in
                          country_activation_count.items()]

        countries_list.sort(key=lambda x: x["country"].lower())
        return countries_list

    class Meta:
        model = Promocode
        fields = (
            "activations_count",
            "countries"
        )
