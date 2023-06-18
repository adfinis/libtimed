import functools
from datetime import date

from libtimed.utils import duration, handle_response


class GetOnlyMixin:
    def post(*args, **kwargs):
        raise NotImplementedError("This model is get-only!")

    def patch(*args, **kwargs):
        raise NotImplementedError("This model is get-only!")


class BaseModel:
    def __init__(self, client) -> None:
        self.client = client

    resource_name: str
    attribute_defaults: list[tuple]
    relationship_defaults: list[tuple]
    filter_defaults: list[tuple]

    def get(self, filters={}, include=None, id=None) -> dict:
        url = f"{self.url}/{id}" if id else self.url
        if id:
            params = include
        else:
            params = self._parsed_defaults(self.__class__.filter_defaults, filters)
        resp = self.client.session.get(url, params=params)
        # add good unified handling here
        return handle_response(resp).json()["data"]

    def post(self, attributes, relationships):
        json = self.parse_post_patch_json(attributes, relationships)
        resp = self.client.session.post(self.url, json=json)
        return resp

    def patch(self, id, attributes, relationships):
        json = self.parse_post_patch_json(attributes, relationships)
        resp = self.client.session.patch(f"{self.url}/{id}", json=json)
        return resp

    def all(self, filters, include=None):
        # self.get but with different defaults
        raise NotImplementedError

    def parse_post_patch_json(self, attributes, relationships):
        cls = self.__class__
        return {
            "data": {
                "type": cls.resource_name,
                "attributes": self._parsed_defaults(cls.attribute_defaults, attributes),
                "relationships": self._parsed_relationships(
                    cls.relationship_defaults, relationships
                ),
            }
        }

    def _id_to_relationship(self, id, resource_name):
        return {
            "data": {
                "type": resource_name,
                "id": id,
            }
        }

    def _parsed_relationships(self, defaults: list[tuple], relationships: dict) -> dict:
        parsed = self._parsed_defaults(defaults, relationships)
        return {
            key: self._id_to_relationship(id, key + "s")
            for key, value in parsed.items()
        }

    def _parsed_value(self, value):
        return value if value != "user-id" else self.client.users.me["id"]

    def _parsed_defaults(self, defaults: list[tuple], values: dict) -> dict:
        return {
            default[0]: self._parsed_value(values.get(default[0]) or default[1])
            for default in defaults
        }

    @functools.cached_property
    def url(self):
        return self.client.url + self.__class__.resource_name


class Users(GetOnlyMixin, BaseModel):
    resource_name = "users"

    @property
    @functools.lru_cache()
    def me(self):
        return self.get(id="me")


class Reports(BaseModel):
    resource_name = "reports"

    attribute_defaults = [
        ("comment", None, str, "Comment -> what exactly did you work on"),
        ("date", date.today(), date, "Date of the report."),
        (
            "duration",
            duration(minutes=15),
            str,
            "Duration, only in 15 min differences.",
        ),
        ("review", False, bool, "Needs to be reviewed."),
        ("not-billable", False, bool, "Is not billable."),
    ]
    relationship_defaults = [
        (
            "user",
            "user-id",
            "The users id, defaults to the logged in users id, another users id may require elevated permissions.",
        ),
        ("task", None, "The tasks id."),
    ]

    filter_defaults = [
        (
            "user",
            "user-id",
            int,
            "The users id, another users id requires elevated permissions.",
        ),
        ("date", date.today(), date, "Date of the report."),
        ("from_date", None, date, "Date of the report."),
        ("to_date", None, date, "Date of the report."),
    ]


class Overtime(
    GetOnlyMixin,
    BaseModel,
):
    resource_name = "worktime-balances"
    filter_defaults = [
        (
            "user",
            "user-id",
            int,
            "The user, using other users might require elevated permissions.",
        ),
        ("date", date.today(), date, "Overtime on that date."),
        ("from_date", None, date, "Overtime from this date."),
        ("to_date", None, date, "Overtime to this date."),
    ]
