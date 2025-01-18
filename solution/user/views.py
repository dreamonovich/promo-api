from django.contrib.auth.hashers import make_password, check_password
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .permissions import IsUserAuthenticated, get_user
from .serializers import RegisterUserSerializer, LoginUserSerializer, UserSerializer, UpdateUserSerializer


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







