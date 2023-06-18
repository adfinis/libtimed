from datetime import timedelta

import requests


def duration(*args, **kwargs):
    return str(timedelta(*args, **kwargs))


def handle_response(resp: requests.Response) -> requests.Response:
    # handle responses
    return resp
