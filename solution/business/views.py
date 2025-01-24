from datetime import datetime

from django.db.models import Q, F, Value
from django.db.models.functions import Coalesce
from rest_framework import status
from django.contrib.auth.hashers import make_password, check_password
from rest_framework.exceptions import NotFound
from rest_framework.generics import CreateAPIView, GenericAPIView, RetrieveUpdateAPIView
from rest_framework.authtoken.models import Token
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView
from app.pagination import PureLimitOffsetPagination
from rest_framework.serializers import ValidationError

from core.utils import is_valid_uuid, clean_country
from business.models import Business, Promocode
from business.permissions import IsBusinessAuthenticated, IsPromocodeOwner, get_business
from business.serializers import RegisterBusinessSerializer, LoginBusinessSerializer, CreatePromocodeSerializer, \
    PromocodeSerializer, ListPromocodesQueryParamsSerializer, PromocodeStatSeriazlier


class LoginBusinessView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = LoginBusinessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

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
    serializer_class = RegisterBusinessSerializer
    def perform_create(self, serializer):
        password = serializer.validated_data['password']
        serializer.validated_data['password'] = make_password(password)

        serializer.validated_data['model_type'] = "BUSINESS"
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

class PromocodeCreateListView(GenericAPIView, CreateModelMixin, ListModelMixin):
    permission_classes = (IsBusinessAuthenticated,)
    pagination_class = PureLimitOffsetPagination

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreatePromocodeSerializer
        return PromocodeSerializer

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        params_serializer = ListPromocodesQueryParamsSerializer(data=self.request.query_params)
        params_serializer.is_valid(raise_exception=True)
        params = params_serializer.validated_data


        sort_by = params.get("sort_by", "created_at")

        queryset = get_business(self.request.user.uuid).promocodes.all()

        if country := self.request.query_params.get("country"):
            country_list = clean_country(country)
            country_filters = Q(target__country__isnull=True)
            for country in country_list:
                country_filters |= Q(target__country__iexact=country)

            queryset = queryset.filter(country_filters)

        if sort_by == "active_from":
            order_field = Coalesce('active_from', Value(datetime.min))
        elif sort_by == "active_until":
            order_field = Coalesce('active_until', Value(datetime.max))
        else:
            order_field = F('created_at')

        return queryset.annotate(sort_field=order_field).order_by("-sort_field")

    def perform_create(self, serializer):
        uuid = self.request.user.uuid
        serializer.validated_data["company"] = Business.objects.get(uuid=uuid)

        return super().perform_create(serializer)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        uuid = response.data["uuid"]
        return Response({"id": uuid}, status=status.HTTP_201_CREATED)

class RetrieveUpdatePromocodeView(RetrieveUpdateAPIView):
    permission_classes = (IsBusinessAuthenticated, IsPromocodeOwner,)
    serializer_class = PromocodeSerializer
    queryset = Promocode.objects.all()
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"

    def retrieve(self, request, uuid,*args, **kwargs):
        if not is_valid_uuid(uuid):
            raise ValidationError("Invalid UUID.")
        return super().retrieve(request, uuid, *args, **kwargs)

    def update(self, request, uuid, *args, **kwargs):
        if not is_valid_uuid(uuid):
            raise ValidationError("Invalid UUID.")

        if not (promocode := Promocode.objects.filter(uuid=uuid).first()):
            raise NotFound("Промокод не надйен.")

        for field in PromocodeSerializer.Meta.read_only_fields:
            if field in request.data:
                raise ValidationError(f"Поле '{field}' не может быть изменено.")

        if (max_count := request.data.get("max_count")) is not None:
            if promocode.mode == "COMMON":
                used_count = promocode.max_count - promocode.common_count
                if used_count > max_count:
                    raise ValidationError("max_count > used_count")

            else:
                if max_count != 1:
                    raise ValidationError("max_count > 1")


        return super().update(request, *args, **kwargs)

class PromocodeStatisticsView(APIView):
    permission_classes = (IsBusinessAuthenticated, IsPromocodeOwner,)

    def get(self, request, *args, **kwargs):
        uuid = self.kwargs["uuid"]
        if not is_valid_uuid(uuid):
            raise ValidationError("Invalid UUID.")

        if not (promocode := Promocode.objects.filter(uuid=uuid).first()):
            raise NotFound("Промокод не надйен.")

        response_data = PromocodeStatSeriazlier(promocode).data
        return Response(response_data)
