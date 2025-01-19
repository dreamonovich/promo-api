from collections import OrderedDict

from rest_framework import serializers


class ClearNullMixin(serializers.Serializer):
    def to_representation(self, instance):
        result = super().to_representation(instance)
        return OrderedDict(
            [(key, result[key]) for key in result if result[key] is not None]
        )