from django.core.validators import MinLengthValidator, MaxLengthValidator, MinValueValidator, MaxValueValidator
from django.db import models
from rest_framework.exceptions import ValidationError

from core.models import EmailPasswordUser


def password_length_validator(value):
    if len(value) > 60:
        raise ValidationError("Password must not exceed 60 characters.")

class TargetInfo(models.Model):
    age = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    country = models.CharField(max_length=2)

class User(EmailPasswordUser):
    name = models.CharField(validators=[MinLengthValidator(1), MaxLengthValidator(100)], max_length=100)
    surname = models.CharField(validators=[MinLengthValidator(1), MaxLengthValidator(120)], max_length=120)
    avatar_url = models.URLField(max_length=350, blank=True, null=True)
    other = models.OneToOneField(TargetInfo, on_delete=models.CASCADE)

    model_type = "user"