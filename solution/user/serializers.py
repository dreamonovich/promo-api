from django.core.validators import RegexValidator, MinLengthValidator, MaxLengthValidator
from drf_writable_nested import WritableNestedModelSerializer
from rest_framework import serializers

from business.models import Promocode, Comment, promocode_is_active, PromocodeUniqueActivation, \
    PromocodeCommonActivation
from core.serializers import ClearNullMixin
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

class UserSerializer(WritableNestedModelSerializer, ClearNullMixin):
    other = TargetInfoSerializer()

    class Meta:
        model = User
        fields = ("name", "surname", "email", "avatar_url", "other")
        read_only_fields = ("other",)

class UpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("name", "surname", "avatar_url", "password")

class FeedQueryParamSerializer(serializers.Serializer):
    limit = serializers.IntegerField(required=False, allow_null=True)
    offset = serializers.IntegerField(required=False, allow_null=True)
    category = serializers.CharField(required=False, allow_null=True)
    active = serializers.BooleanField(required=False, allow_null=True)

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

    def get_active(self, obj):
        return promocode_is_active(obj)

    def get_like_count(self, obj):
        return obj.likes.count()

    def get_is_activated_by_user(self, obj):
        user = self.context["user"]
        is_common_activated = PromocodeCommonActivation.objects.filter(user=user, promocode_instanse__promocode_set=obj).exists()
        is_unique_activated = PromocodeUniqueActivation.objects.filter(user=user, promocode_instanse__promocode_set=obj).exists()

        return is_common_activated or is_unique_activated

    def get_is_liked_by_user(self, obj):
        return obj.likes.filter(user=self.context["user"]).exists()

    def get_comment_count(self, obj):
        return obj.comments.count()

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

class CreateCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ("text",)

class CommentUserSerializer(serializers.ModelSerializer, ClearNullMixin):
    class Meta:
        model = User
        fields = (
            "name",
            "surname",
            "avatar_url"
        )

class RetrieveCommentSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()

    def get_author(self, obj):
        return CommentUserSerializer(obj.user).data

    def get_id(self, obj):
        return obj.uuid

    def get_date(self, obj):
        return obj.created_at.strftime('%Y-%m-%dT%H:%M:%S') + "Z03:00"

    class Meta:
        model = Comment
        fields = (
            "id",
            "text",
            "date",
            "author"
        )

class UpdateCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ("text",)

class ListCommentsQueryParamSerializer(serializers.Serializer):
    limit = serializers.IntegerField(required=False)
    offset = serializers.IntegerField(required=False)

class HistoryQueryParamSerializer(serializers.Serializer):
    limit = serializers.IntegerField(required=False, allow_null=True)
    offset = serializers.IntegerField(required=False, allow_null=True)
