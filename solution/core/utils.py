import uuid
from django_countries.fields import countries as isocountries
from rest_framework.exceptions import ValidationError


def is_valid_uuid(*uuid_list) -> bool:
    try:
        for uuid_val in uuid_list:
            uuid.UUID(str(uuid_val))
        return True
    except ValueError:
        return False


def validate_country_code(*countries):
    for country in countries:
        if not isinstance(country, str):
            raise ValidationError("not valid country")
        if country.upper() not in dict(isocountries):
            raise ValidationError(f'{country} is not a valid ISO 3166-1 alpha-2 country code')

def clean_country(country) -> list[str]:
    if isinstance(country, str):
        country = country.strip().split(',')
    for country_item in country:
        if len(country_item) != 2 or not isinstance(country_item, str):
            raise ValidationError

    return country