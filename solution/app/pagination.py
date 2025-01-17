from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class PureLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 10

    def get_paginated_response(self, data):
        return Response(
            data,
            headers={
                "X-Total-Count": self.count,
            }
        )