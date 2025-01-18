from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from django.contrib.auth.hashers import make_password, check_password
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import NotFound
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from app.pagination import PureLimitOffsetPagination
from business.models import Promocode, PromocodeAction
from .models import User
from .permissions import IsUserAuthenticated, get_user
from .serializers import RegisterUserSerializer, LoginUserSerializer, UserSerializer, UpdateUserSerializer, \
    FeedQueryParamSerializer, PromocodeForUserSerializer


class LoginUserView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = LoginUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        if not (user := User.objects.filter(email=email).first()) or not check_password(password, user.password):
            return Response({
                "message": "Неверный email или password.",
            }, status=status.HTTP_401_UNAUTHORIZED
            )

        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)

        return Response({
            "token": token.key,
        })

class RegisterUserView(CreateAPIView):
    serializer_class = RegisterUserSerializer

    def perform_create(self, serializer):
        password = serializer.validated_data['password']
        serializer.validated_data['password'] = make_password(password)

        serializer.validated_data['model_type'] = "USER"
        serializer.save()

    def create(self, request, *args, **kwargs):
        email = request.data.get("email")
        if User.objects.filter(email=email).exists():
            return Response({"message": "Пользователь с указанным email уже зарегистрирован."},
                            status=status.HTTP_409_CONFLICT)

        response = super().create(request, *args, **kwargs)

        email = response.data.get("email")
        user = User.objects.get(email=email)

        token = Token.objects.create(user=user)

        return Response({
            "token": token.key,
            "company_id": user.uuid
        })

class RetrieveUpdateUserView(APIView):
    permission_classes = (IsUserAuthenticated,)
    serializer_class = UserSerializer

    def get(self, request, *args, **kwargs):
        user = get_user(request.user.uuid)
        serializer = UserSerializer(user)

        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        user = get_user(request.user.uuid)

        serializer = UpdateUserSerializer(
            user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        if password := serializer.validated_data.get('password'):
            serializer.validated_data["password"] = make_password(password)
            Token.objects.filter(user=user).delete()
        serializer.save()

        res_ser = UserSerializer(user)
        return Response(res_ser.data)



class FeedView(ListAPIView):
    permission_classes = (IsUserAuthenticated,)
    pagination_class = PureLimitOffsetPagination
    serializer_class = PromocodeForUserSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        user = get_user(self.request.user.uuid)
        params_serializer = FeedQueryParamSerializer(data=self.request.query_params)
        params_serializer.is_valid(raise_exception=True)
        params = params_serializer.validated_data

        category = params.get('category')
        active = params.get('active')
        age = user.other.age
        country = user.other.country

        queryset = Promocode.objects.all()


        if category is not None:
            queryset = queryset.filter(target__categories__icontains=category)

        if active is not None:
            current_time = timezone.now() + timedelta(hours=3)

            active_filter = Q(active_from__isnull=True) | Q(active_from__lte=current_time)
            active_filter &= Q(active_until__isnull=True) | Q(active_until__gte=current_time)
            # active_filter &= Q(mode='COMMON', max_count__gt=F('company__promocodes__count')) | Q(mode='UNIQUE', # TODO: wrong
            #                                                                                      promo_unique__len__gt=0)

            if active:
                queryset = queryset.filter(active_filter)
            else:
                queryset = queryset.exclude(active_filter)

        target_filter = (
                (Q(target__age_from__isnull=True) | Q(target__age_from__lte=age)) &
                (Q(target__age_until__isnull=True) | Q(target__age_until__gte=age)) &
                (Q(target__country__isnull=True) | Q(target__country=country))
        )
        queryset = queryset.filter(target_filter)

        return queryset

class RetrievePromocodeForUserView(RetrieveAPIView):
    permission_classes = (IsUserAuthenticated,)
    serializer_class = PromocodeForUserSerializer
    queryset = Promocode.objects.all()
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"

class LikePromocodeView(CreateAPIView):
    permission_classes = (IsUserAuthenticated,)

    action_type = "like"

    def action(self, user: User, promocode: Promocode) -> None:
        if (
            not (action_qs := PromocodeAction.objects.filter(profile=user, promocode=promocode))
            or action_qs.first().type != self.action_type
        ):
            action_qs.delete()
            PromocodeAction.objects.create(profile=user, promocode=promocode, type=self.action_type)

    def get(self, request, uuid, *args, **kwargs) -> Response:

        if not (
            promocode := Promocode.objects.filter(uuid=uuid).first()
        ):
            raise NotFound(f"{uuid}")

        self.action(get_user(self.request.user.uuid), promocode)

        return Response(
            {
                "status": "ok"
            }
        )

    def delete(self, request, uuid, *args, **kwargs) -> Response:
        if not (
                promocode := Promocode.objects.filter(uuid=uuid).first()
        ):
            raise NotFound(f"{uuid}")

        PromocodeAction.objects.filter(profile=get_user(self.request.user.uuid), promocode=promocode).delete()

        return Response(
            {
                "status": "ok"
            }
        )


