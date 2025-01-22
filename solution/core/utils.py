import uuid
from django_countries.fields import countries
from rest_framework.exceptions import ValidationError


def is_valid_uuid(*uuid_list) -> bool:
    try:
        for uuid_val in uuid_list:
            uuid.UUID(str(uuid_val))
        return True
    except ValueError:
        return False


def validate_country_code(country):
    if not isinstance(country, str):
        raise ValidationError("not valid country")
    if country.upper() not in dict(countries):
        raise ValidationError(f'{country} is not a valid ISO 3166-1 alpha-2 country code')
