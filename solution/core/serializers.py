from collections import OrderedDict

from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class ClearNullMixin(serializers.Serializer):
    def to_representation(self, instance):
        result = super().to_representation(instance)

        if result.get("max_count") is not None and result.get("target") is None: # =)
            result["target"] = {}

        return OrderedDict(
            [(key, result[key]) for key in result if result[key] is not None]
        )

class StrictFieldMixin:
    base_type = None

    def to_internal_value(self, data):
        if not isinstance(data, self.base_type):
            raise ValidationError(f"field unsupported type: {type(data)}")
        return super().to_internal_value(data)


class StrictCharField(StrictFieldMixin, serializers.CharField):
    base_type = str


class StrictBooleanField(StrictFieldMixin, serializers.BooleanField):
    base_type = bool


class StrictIntegerField(StrictFieldMixin, serializers.IntegerField):
    base_type = int

class StrictURLField(StrictFieldMixin, serializers.URLField):
    base_type = str