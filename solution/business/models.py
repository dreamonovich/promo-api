import uuid
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, MaxLengthValidator, MinValueValidator, \
    MaxValueValidator
from django.contrib.postgres.fields import ArrayField
from django.db import models
from rest_framework import serializers

from core.models import EmailPasswordUser


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
    target = models.ForeignKey(Target, on_delete=models.CASCADE, null=True)
    max_count = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100000000)])
    active_from = models.DateTimeField(blank=True, null=True)
    active_until = models.DateTimeField(blank=True, null=True)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES)
    promo_common = models.CharField(
        validators=[MinLengthValidator(5), MaxLengthValidator(30)],
        max_length=30,
        blank=True,
        null=True,
    )
    promo_unique = ArrayField(
        models.CharField(
            validators=[MinLengthValidator(3), MaxLengthValidator(30)],
            max_length=30,
        ),
        validators=[MinLengthValidator(1), MaxLengthValidator(5000)],
        max_length=5000,
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.mode == 'COMMON':
            if not self.promo_common:
                raise serializers.ValidationError("promo_common не может быть пустым если mode=COMMON.")
        elif self.mode == 'UNIQUE':
            if not self.promo_unique or len(self.promo_unique) == 0:
                raise serializers.ValidationError("promo_unique не может быть пустым если mode=UNIQUE.")
            self.max_count = 1
        if self.target and self.target.age_from and self.target.age_until:
            if self.target.age_from > self.target.age_until:
                raise serializers.ValidationError("age_from не должен превышать age_until.")
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.uuid)






