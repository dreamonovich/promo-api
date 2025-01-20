import json
import datetime as dt
import redis
import requests
from requests import Response

from app.settings import ANTIFRAUD_ADDRESS, REDIS_HOST, REDIS_PORT

redis_conn = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT
)

def _get_user_cached_info(user_email: str) -> dict: # utc time
    user_cached_info = {}
    if byted_user_cached_info := redis_conn.get(user_email):
        user_cached_info = json.loads(byted_user_cached_info)
    return user_cached_info

def _set_user_cached_info(user_email: str, cache_until: str, success: bool):
    info = {
        "cache_until": cache_until,
        "success": success
    }
    redis_conn.set(user_email, json.dumps(info))

def _get_antifraud_response(user_email: str, promocode_uuid: str) -> Response:
    data = {
        "user_email": user_email,
        "promo_id": promocode_uuid
    }
    antifraud_response = requests.post(f"http://{ANTIFRAUD_ADDRESS}/api/validate", json=data)
    if antifraud_response.status_code != 200:
        antifraud_response = requests.post(f"http://{ANTIFRAUD_ADDRESS}/api/validate", json=data)

    return antifraud_response

def _is_cache_until_passed(cache_until):
    cache_until = dt.datetime.strptime(cache_until, '%Y-%m-%dT%H:%M:%S.%f')
    return cache_until < dt.datetime.now()

def antifraud_success(user_email: str, promocode_uuid: str) -> bool:
    cached_info = _get_user_cached_info(user_email)

    cache_until = cached_info.get("cache_until")
    success = cached_info.get("success")

    if cached_info and not _is_cache_until_passed(cache_until):
        return success

    antifraud_response = _get_antifraud_response(user_email, promocode_uuid)
    print("antifraud_response", antifraud_response)
    if antifraud_response.status_code != 200:
        return False

    antifraud_response_data = antifraud_response.json()
    success = antifraud_response_data.get("ok")
    cache_until = antifraud_response_data.get("cache_until")

    if cache_until:
        _set_user_cached_info(user_email, cache_until, success)

    return success

