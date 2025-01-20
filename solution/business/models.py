import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, MaxLengthValidator, MinValueValidator, \
    MaxValueValidator
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone
from rest_framework import serializers

from core.models import EmailPasswordUser
from user.models import User


def password_length_validator(value):
    if len(value) > 60:
        raise ValidationError("Password must not exceed 60 characters.")

class Target(models.Model):
    age_from = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        blank=True,
        null=True,

    )
    age_until = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        blank=True,
        null=True,
    )
    country = models.CharField(max_length=2, blank=True, null=True) # TODO: валидация по ISO 3166-1 alpha-2
    categories = ArrayField(
        models.CharField(validators=[MinLengthValidator(2), MaxLengthValidator(20)], max_length=20),
        max_length=20,
        blank=True,
        null=True,
    )


class Business(EmailPasswordUser):
    name = models.CharField(
        validators=[MinLengthValidator(5)],
        max_length=50,
    )

    def __str__(self):
        return f"{self.name} ({self.uuid})"


class Promocode(models.Model):
    MODE_CHOICES = [
        ('COMMON', 'Common'),
        ('UNIQUE', 'Unique')
    ]

    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="promocodes")
    description = models.CharField(
        max_length=300,
        validators=[
            MinLengthValidator(10),
            MaxLengthValidator(300),
        ],
    )
    image_url = models.URLField(
        max_length=350,
        blank=True,
        null=True,
    )
    target = models.OneToOneField(Target, on_delete=models.CASCADE, null=True)
    max_count = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100000000)])
    common_count = models.IntegerField(default=0)
    unique_count = models.IntegerField(default=0)
    common_activations_count = models.IntegerField(default=0)
    unique_activations_count = models.IntegerField(default=0)
    active_from = models.DateTimeField(blank=True, null=True)
    active_until = models.DateTimeField(blank=True, null=True)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.target and self.target.age_from and self.target.age_until:
            if self.target.age_from > self.target.age_until:
                raise serializers.ValidationError("age_from не должен превышать age_until.")
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.uuid)

class PromocodeCommonInstance(models.Model):
    promocode = models.CharField(
        max_length=30,
        validators=[MinLengthValidator(5), MaxLengthValidator(30)],
    )
    is_activated = models.BooleanField(default=False)
    promocode_set = models.ForeignKey('Promocode', on_delete=models.CASCADE, related_name='common_code')

class PromocodeUniqueInstance(models.Model):
    promocode = models.CharField(
        max_length=30,
        validators=[MinLengthValidator(5), MaxLengthValidator(30)],
    )
    is_activated = models.BooleanField(default=False)
    promocode_set = models.ForeignKey('Promocode', on_delete=models.CASCADE, related_name='unique_codes')

def promocode_is_active(promocode, current_time=None):
    if current_time is None:
        current_time = timezone.now() + timedelta(hours=3)  # UTC+3

    if promocode.active_from and promocode.active_from > current_time:
        return False
    if promocode.active_until and promocode.active_until < current_time:
        return False

    if promocode.mode == 'COMMON':
        if promocode.common_count <= 0:
            return False
    elif promocode.mode == 'UNIQUE':
        if promocode.unique_count <= 0:
            return False

    return True


class PromocodeAction(models.Model):
    promocode = models.ForeignKey(Promocode, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    type = models.CharField(max_length=10, db_index=True)

    class Meta:
        unique_together = ("promocode", "user")

class Comment(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    promocode = models.ForeignKey(Promocode, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.CharField(validators=[MinLengthValidator(10), MaxLengthValidator(1000)], max_length=1000)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.uuid)

class PromocodeActivation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="users_activated")

class PromocodeUniqueActivation(PromocodeActivation):
    promocode_instanse = models.ForeignKey(PromocodeUniqueInstance, on_delete=models.CASCADE, related_name="unique_activations")
    created_at = models.DateTimeField(auto_now_add=True)

class PromocodeCommonActivation(PromocodeActivation):
    promocode_instanse = models.ForeignKey(PromocodeCommonInstance, on_delete=models.CASCADE, related_name="common_activations")
    created_at = models.DateTimeField(auto_now_add=True)