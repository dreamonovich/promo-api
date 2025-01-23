import uuid
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinLengthValidator, MaxLengthValidator, RegexValidator
from django.db import models
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import ValidationError


class BearerTokenAuthentication(TokenAuthentication):
    keyword = 'Bearer'

def password_length_validator(value):
    if len(value) > 60:
        raise ValidationError("Password must not exceed 60 characters.")


class EmailPasswordUser(AbstractUser):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(validators=[MinLengthValidator(8), MaxLengthValidator(120)], max_length=120)
    password = models.CharField(
        validators=[
            MinLengthValidator(8),
            password_length_validator,
            RegexValidator(
                regex=r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
            )
        ],
        max_length=256,
    )

    model_type = models.CharField(choices=[('BUSINESS', 'Business'), ('USER', 'User')], blank=True, null=True)
    username = models.CharField(max_length=120)
    USERNAME_FIELD = "uuid"
    REQUIRED_FIELDS = ["password"]

    def __str__(self):
        return str(self.uuid)
