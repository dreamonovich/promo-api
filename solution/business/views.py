from rest_framework import status
from django.contrib.auth.hashers import make_password, check_password
from rest_framework.generics import CreateAPIView, ListAPIView, GenericAPIView, RetrieveAPIView, RetrieveUpdateAPIView
from rest_framework.authtoken.models import Token
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import models
from app.pagination import PureLimitOffsetPagination
from business import serializers
from rest_framework.serializers import ValidationError
from business.models import Business, Promocode
from business.permissions import IsBusinessAuthenticated, IsPromocodeOwner
from business.serializers import CreateBusinessSerializer, LoginBusinessSerializer, CreatePromocodeSerializer, \
    PromocodeSerializer, ListPromocodesQueryParamsSerializer


class LoginBusinessView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = LoginBusinessSerializer(data=request.data)
        validated_data = serializer.validate(request.data)

        email = validated_data['email']
        password = validated_data['password']

        if not (business := Business.objects.filter(email=email).first()) or not check_password(password, business.password):
            return Response({
                "message": "Неверный email или password.",
            }, status=status.HTTP_401_UNAUTHORIZED
            )

        Token.objects.filter(user=business).delete()
        token = Token.objects.create(user=business)

        return Response({
            "token": token.key,
        })

class RegisterBusinessView(CreateAPIView):
    serializer_class = CreateBusinessSerializer
    def perform_create(self, serializer):
        password = serializer.validated_data['password']
        serializer.validated_data['password'] = make_password(password)
        serializer.save()

    def create(self, request, *args, **kwargs):
        email = request.data.get("email")
        if Business.objects.filter(email=email).exists():
            return Response({"message": "Компания с указанным email уже зарегистрирован."},
                            status=status.HTTP_409_CONFLICT)

        response = super().create(request, *args, **kwargs)

        email = response.data.get("email")
        business = Business.objects.get(email=email)

        token = Token.objects.create(user=business)

        return Response({
            "token": token.key,
            "company_id": business.uuid
        })

def clean_country(country) -> list[str]:
    if isinstance(country, str):
        country = country.strip().split(',')
    for country_item in country:
        if len(country_item) != 2 or not isinstance(country_item, str):
            raise ValidationError

    return country

class PromocodeView(GenericAPIView, CreateModelMixin, ListModelMixin):
    permission_classes = (IsBusinessAuthenticated,)
    pagination_class = PureLimitOffsetPagination

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreatePromocodeSerializer
        return PromocodeSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        params_serializer = ListPromocodesQueryParamsSerializer(data=self.request.query_params)
        params_serializer.is_valid(raise_exception=True)
        params = params_serializer.validated_data

        sort_by = params.get("sort_by", "created_at")

        queryset = self.request.user.promocodes.all()

        if country := self.request.query_params.get("country"):
            country_list = clean_country(country)
            queryset = queryset.filter(
                models.Q(target__isnull=True) | models.Q(target__country__in=country_list)
            )

        return queryset.order_by(f"-{sort_by}")

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.validated_data["company"] = self.request.user
        return super().perform_create(serializer)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        uuid = response.data.get("uuid")
        return Response({"id": uuid}, status=status.HTTP_201_CREATED)

class RetrievePromocodeView(RetrieveUpdateAPIView):
    permission_classes = (IsBusinessAuthenticated, IsPromocodeOwner)
    serializer_class = PromocodeSerializer
    queryset = Promocode.objects.all()
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"

    def update(self, request, *args, **kwargs):
        for field in PromocodeSerializer.Meta.read_only_fields:
            if field in request.data:
                raise ValidationError(f"Поле '{field}' не может быть изменено.")
        return super().update(request, *args, **kwargs)



