import logging
from collections.abc import MutableMapping
from typing import Any


def pytest_tavern_beta_before_every_request(request_args: MutableMapping) :
    logging.info(f"Request: {request_args['method']} {request_args['url']}\n{request_args['headers']}\n{request_args.get('body', "<no body>")}")

def pytest_tavern_beta_after_every_response(expected: Any, response: Any) -> None:
    logging.info(f"Response: {response.status_code} {response.text}")