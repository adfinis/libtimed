#!/usr/bin/env python

import requests
import functools
from datetime import date

from libtimed.oidc import OIDCClient
class TimedAPI:
    def __init__(self, token, url, api_namespace):
        self.token = token
        self.url = url
        self.api_namespace = api_namespace
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.session.headers["Content-Type"] = "application/vnd.api+json"

    def request(self, resource, params=None):
        url = self.base_url + resource

        resp = self.session.get(url, params=params)
        # do handling here
        return resp.json()

    def post(self, resource, params=None):
        url = self.base_url + resource

        resp = self.session.post(url, json=params)
        # do handling here
        return resp.json()

    def _parse_params(self, defaults, kwargs):
        """Parse defaults and kwargs into a params dict"""
        return [kwargs.get(key) or defaults[key] for key in defaults.keys()]

    @property
    @functools.lru_cache()
    def me(self, params=None):
        return self.request('users/me', params)

    @property
    @functools.lru_cache()
    def id(self):
        return self.me["data"]["id"]

    @property
    @functools.lru_cache()
    def location(self):
        return self.me["data"]["id"]

    @property
    def overtime(self, **kwargs):
        defaults = [
            ("user", self.me.id, int, "The user, using other users might require elevated permissions."),
            ("date", date.today(), date, "Overtime on that date."),
            ("from_date", None, date, "Overtime from this date."),
            ("to_date", None, date, "Overtime to this date."),
        ]
        return self.request('worktime-balances', self._parse_params(defaults, kwargs))

    @property
    @functools.lru_cache()
    def reports(self, **kwargs):
        defaults = [
            ("user", self.me["data"]["id"], int, "The user which the report belongs to"),
            ("date", date.today(), date, "The date on which to look for reports"),
            ("editable", None, bool, "Only editable projects"),
            ("from_date", None, date, "Reports from this date on"),
            ("to_date", None, date, "Reports to this date"),
        ]
        return self.request('reports', self._parse_params(defaults, kwargs))

    @property
    @functools.lru_cache()
    def tasks(self, project):
        params = {"project": project["id"]}
        return self.request('tasks', params)

    @property
    @functools.lru_cache()
    def customers(self):
        return self.request('customers')

    @property
    @functools.lru_cache()
    def projects(self, customer):
        params = {"customer": customer["id"]}
        return self.request('projects', params)

    @property
    def base_url(self):
        return f"{self.url}/{self.api_namespace}/"


if __name__ == "__main__":
    client_id = "timed-client-id"
    auth_endpoint = (
        "https://sso.example.com/auth/realms/example/protocol/openid-connect/auth"
    )
    token_endpoint = (
        "https://sso.example.com/auth/realms/example/protocol/openid-connect/token"
    )
    auth_path = "timedctl/auth"

    oidc_client = OIDCClient(client_id, auth_endpoint, token_endpoint, auth_path)
    token = oidc_client.authorize()

    api = TimedAPI(token, "https://timed.example.com", "api/v1")


    # input = input("What did you do today?")
    # json = {
    #     "data": {
    #         "type": "reports",
    #         "attributes": {
    #             "comment": input,
    #             "date": "2023-06-16",
    #             "duration": "00:15:00",
    #             "remaining-effort": None,
    #             "review": False,
    #             "rejected": False,
    #             "not-billable": False,
    #             "billed": False,
    #         },
    #         "relationships": {
    #             # user can be dried
    #             "task": { "data": {"type":"tasks", "id":"3604682"}},
    #             "user": { "data": {"type":"users", "id":"317"}},
    #         },
    #     }
    # }

    # api.post("reports", params=json)

    print(api.overtime)
