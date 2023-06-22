from datetime import timedelta

import requests


def serialize_duration(duration: timedelta) -> str:
    days = ""
    if duration.days != 0:
        days = str(duration.days) + " "
    hours, minutes, seconds = str(duration).split(" ")[-1].split(":")
    return f"{days}{hours.zfill(2)}:{minutes}:{seconds}"


def deserialize_duration(duration: str) -> timedelta:
    days = 0
    if len(duration.split(" ")) != 1:
        days, duration = duration.split(" ")
    hours, minutes, seconds = map(int, duration.split(":"))
    delta = timedelta(days=int(days), hours=hours, minutes=minutes, seconds=seconds)
    return delta


def handle_response(resp: requests.Response) -> requests.Response:
    # handle responses
    return resp
