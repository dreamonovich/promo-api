from collections import OrderedDict

from rest_framework import serializers


class ClearNullMixin(serializers.Serializer):
    def to_representation(self, instance):
        result = super().to_representation(instance)

        if result.get("max_count") is not None and (target := result.get("target")) is None: # =)
            result["target"] = {}

        return OrderedDict(
            [(key, result[key]) for key in result if result[key] is not None]
        )