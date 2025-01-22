from itertools import chain
from typing import Union

from django.utils import timezone
from django.db.models import Q, F
from datetime import timedelta
from django.contrib.auth.hashers import make_password, check_password
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import NotFound, ValidationError, PermissionDenied
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView, GenericAPIView
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView

from app.pagination import PureLimitOffsetPagination
from core.utils import is_valid_uuid
from business.models import Promocode, PromocodeAction, Comment, promocode_is_active, Target, PromocodeUniqueInstance, \
    PromocodeCommonInstance, PromocodeCommonActivation, PromocodeUniqueActivation
from .antifraud import antifraud_success
from .models import User, TargetInfo
from .permissions import IsUserAuthenticated, get_user, IsCommentOwner
from .serializers import RegisterUserSerializer, LoginUserSerializer, UserSerializer, UpdateUserSerializer, \
    FeedQueryParamSerializer, PromocodeForUserSerializer, CreateCommentSerializer, RetrieveCommentSerializer, \
    UpdateCommentSerializer, HistoryQueryParamSerializer


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
            "token": token.key
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
        serializer.save()

        res_ser = UserSerializer(user)
        return Response(res_ser.data)


class FeedView(ListAPIView):
    permission_classes = (IsUserAuthenticated,)
    pagination_class = PureLimitOffsetPagination
    serializer_class = PromocodeForUserSerializer

    def get_serializer_context(self):  # for is_liked_by_user
        context = super().get_serializer_context()
        context.update({"user": get_user(self.request.user.uuid)})
        return context

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        user = get_user(self.request.user.uuid)
        params_serializer = FeedQueryParamSerializer(data=self.request.query_params)
        params_serializer.is_valid(raise_exception=True)
        params = params_serializer.validated_data

        category = params.get('category', None)
        active = params.get('active', None)
        age = user.other.age
        country = user.other.country

        queryset = Promocode.objects.all()

        if category is not None:
            queryset = queryset.filter(target__categories__icontains=category)

        if active is not None:
            current_time = timezone.now() + timedelta(hours=3)

            active_filter = Q(active_from__isnull=True) | Q(active_from__lte=current_time)
            active_filter &= Q(active_until__isnull=True) | Q(active_until__gte=current_time)
            active_filter &= Q(mode='COMMON', common_count__gt=0) | Q(mode='UNIQUE', unique_count__gt=0)

            if active:
                queryset = queryset.filter(active_filter)
            else:
                queryset = queryset.exclude(active_filter)

        target_filter = (
                (Q(target__age_from__isnull=True) | Q(target__age_from__lte=age)) &
                (Q(target__age_until__isnull=True) | Q(target__age_until__gte=age)) &
                (Q(target__country__isnull=True) | Q(target__country__iexact=country))
        )
        queryset = queryset.filter(target_filter)

        return queryset.order_by("-created_at")


class RetrievePromocodeForUserView(RetrieveAPIView):
    permission_classes = (IsUserAuthenticated,)
    serializer_class = PromocodeForUserSerializer
    queryset = Promocode.objects.all()
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"

    def get_serializer_context(self):  # for is_liked_by_user
        context = super().get_serializer_context()
        context.update({"user": get_user(self.request.user.uuid)})
        return context

    def retrieve(self, request, uuid, *args, **kwargs):
        if not is_valid_uuid(uuid):
            raise ValidationError("Invalid UUID.")
        return super().retrieve(request, uuid, *args, **kwargs)


class LikePromocodeView(APIView):
    permission_classes = (IsUserAuthenticated,)

    action_type = "like"

    def action(self, user: User, promocode: Promocode) -> None:
        if (
                not (action_qs := PromocodeAction.objects.filter(user=user, promocode=promocode))
                or action_qs.first().type != self.action_type
        ):
            action_qs.delete()
            PromocodeAction.objects.create(user=user, promocode=promocode, type=self.action_type)

    def post(self, request, uuid, *args, **kwargs) -> Response:
        if not is_valid_uuid(uuid):
            raise ValidationError("Invalid UUID.")

        if not (
                promocode := Promocode.objects.filter(uuid=uuid).first()
        ):
            raise NotFound("Промокод не найден.")

        self.action(get_user(self.request.user.uuid), promocode)

        return Response(
            {
                "status": "ok"
            }
        )

    def delete(self, request, uuid, *args, **kwargs) -> Response:
        if not is_valid_uuid(uuid):
            raise ValidationError("Invalid UUID.")

        if not (
                promocode := Promocode.objects.filter(uuid=uuid).first()
        ):
            raise NotFound("Промокод не найден.")

        PromocodeAction.objects.filter(user=get_user(self.request.user.uuid), promocode=promocode).delete()

        return Response(
            {
                "status": "ok"
            }
        )


class CreateListCommentView(GenericAPIView, CreateModelMixin, ListModelMixin):
    permission_classes = (IsUserAuthenticated,)
    pagination_class = PureLimitOffsetPagination
    serializer_class = RetrieveCommentSerializer

    def get(self, request, *args, **kwargs) -> Response:
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, uuid, *args, **kwargs):
        if not is_valid_uuid(uuid):
            raise ValidationError("Invalid UUID.")

        if not (
                promocode := Promocode.objects.filter(uuid=uuid).first()
        ):
            raise NotFound("Промокод не найден.")

        serializer = CreateCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = Comment.objects.create(
            user=get_user(self.request.user.uuid),
            promocode=promocode,
            text=serializer.validated_data['text'],
        )

        response_data = RetrieveCommentSerializer(comment).data
        return Response(response_data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        uuid = self.kwargs.get("uuid")
        if not is_valid_uuid(uuid):
            raise ValidationError("Invalid UUID.")

        params_serializer = FeedQueryParamSerializer(data=self.request.query_params)
        params_serializer.is_valid(raise_exception=True)

        if not Promocode.objects.filter(uuid=uuid).exists():
            raise NotFound("Промокод не найден.")

        queryset = Comment.objects.filter(promocode__uuid=uuid)

        return queryset.order_by("-created_at")


class RetrieveUpdateDeleteCommentView(APIView):
    permission_classes = (IsUserAuthenticated, IsCommentOwner,)

    def get(self, request, *args, **kwargs):
        promo_uuid = self.kwargs.get("promo_uuid")
        comment_uuid = self.kwargs.get("comment_uuid")

        if not is_valid_uuid(promo_uuid, comment_uuid):
            raise ValidationError("Invalid UUID.")

        if not (comment := Comment.objects.filter(promocode__uuid=promo_uuid, uuid=comment_uuid).first()):
            raise NotFound("Комментарий не найден.")
        response_data = RetrieveCommentSerializer(comment).data
        return Response(response_data)

    def put(self, request, *args, **kwargs):
        promo_uuid = self.kwargs.get("promo_uuid")
        comment_uuid = self.kwargs.get("comment_uuid")

        if not is_valid_uuid(promo_uuid, comment_uuid):
            raise ValidationError("Invalid UUID.")

        if not (comment := Comment.objects.filter(promocode__uuid=promo_uuid, uuid=comment_uuid).first()):
            raise NotFound("Комментарий не найден.")

        if not comment.user == get_user(self.request.user.uuid):
            raise PermissionDenied("Низя")

        serialier = UpdateCommentSerializer(data=request.data)
        serialier.is_valid(raise_exception=True)

        comment.text = serialier.validated_data['text']
        comment.save()

        response_data = RetrieveCommentSerializer(comment).data
        return Response(response_data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        promo_uuid = self.kwargs.get("promo_uuid")
        comment_uuid = self.kwargs.get("comment_uuid")

        if not is_valid_uuid(promo_uuid, comment_uuid):
            raise ValidationError("Invalid UUID.")

        if not (comment := Comment.objects.filter(promocode__uuid=promo_uuid, uuid=comment_uuid).first()):
            raise NotFound("Комментарий не найден.")

        if not comment.user == get_user(self.request.user.uuid):
            raise PermissionDenied("Низя")

        comment.delete()

        return Response(
            {"status": "ok"}
        )


def user_is_targeted(user_info: TargetInfo, promocode_target: Target) -> bool:
    targeted_age_until = promocode_target.age_until
    targeted_age_from = promocode_target.age_from
    targeted_country = promocode_target.country
    if targeted_age_until and user_info.age > targeted_age_until:
        return False
    if targeted_age_from and user_info.age < targeted_age_from:
        return False
    if targeted_country and user_info.country != targeted_country:
        print("TARGETED COUNTRY IS", targeted_country)
        return False
    return True


def activate_promocode(user: User, promocode_instanse: Union[PromocodeUniqueInstance, PromocodeCommonInstance],
                       promocode: Promocode):
    promocode_instanse.is_activated = True
    promocode_instanse.save()

    if isinstance(promocode_instanse, PromocodeCommonInstance):
        PromocodeCommonActivation.objects.create(user=user, promocode_instanse=promocode_instanse)
        promocode.common_count -= 1
        promocode.common_activations_count += 1
    else:
        PromocodeUniqueActivation.objects.create(user=user, promocode_instanse=promocode_instanse)
        promocode.unique_count -= 1
        promocode.unique_activations_count += 1
    promocode.save()


class ActivatePromocode(APIView):
    permission_classes = (IsUserAuthenticated,)

    def post(self, request, *args, **kwargs):
        promo_uuid = self.kwargs.get("promo_uuid")
        user = get_user(request.user.uuid)

        if not is_valid_uuid(promo_uuid):
            raise ValidationError("Invalid UUID.")

        if not (
                promocode := Promocode.objects.filter(uuid=promo_uuid).first()
        ):
            raise NotFound("Промокод не найден.")

        if promocode.mode == "COMMON":
            promocode_instanse = promocode.common_code.first()
        else:  # unique mode
            promocode_instanse = promocode.unique_codes.filter(is_activated=False).first()

        if not promocode_is_active(promocode) \
                or not user_is_targeted(user.other, promocode.target) \
                or not antifraud_success(user.email, promo_uuid):
            return Response(
                {"detail": "Вы не можете активировать этот промокод."},
                status=status.HTTP_403_FORBIDDEN,
            )

        activate_promocode(user, promocode_instanse, promocode)
        return Response(
            {"promo": promocode_instanse.promocode},
        )


class ActivationHistory(ListAPIView):
    permission_classes = (IsUserAuthenticated,)
    pagination_class = PureLimitOffsetPagination
    serializer_class = PromocodeForUserSerializer

    def get_serializer_context(self):  # for is_liked_by_user
        context = super().get_serializer_context()
        context.update({"user": get_user(self.request.user.uuid)})
        return context

    def get_queryset(self):
        user = get_user(self.request.user.uuid)
        params_serializer = HistoryQueryParamSerializer(data=self.request.query_params)
        params_serializer.is_valid(raise_exception=True)

        common_queryset = Promocode.objects.filter(
            common_code__common_activations__user=user
        ).annotate(activation_created_at=F('common_code__common_activations__created_at'))

        unique_queryset = Promocode.objects.filter(
            unique_codes__unique_activations__user=user
        ).annotate(activation_created_at=F('unique_codes__unique_activations__created_at'))

        queryset = sorted(
            chain(common_queryset, unique_queryset),
            key=lambda promo: promo.activation_created_at,
            reverse=True
        )

        return queryset

