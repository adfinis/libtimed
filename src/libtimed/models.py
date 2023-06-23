import functools
from datetime import date, datetime, timedelta

from libtimed.utils import deserialize_duration, handle_response, serialize_duration


class GetOnlyMixin:
    message = "This model is get-only!"

    def post(self, *args, **kwargs):
        raise NotImplementedError(self.__class__.message)

    def patch(self, *args, **kwargs):
        raise NotImplementedError(self.__class__.message)


class BaseModel:
    def __init__(self, client) -> None:
        self.client = client

    resource_name: str
    attribute_defaults: list[tuple]
    relationship_defaults: list[tuple]
    filter_defaults: list[tuple]

    def get(self, filters={}, include=None, id=None):
        url = f"{self.url}/{id}" if id else self.url
        if id:
            params = include
        else:
            params = self._parsed_defaults(self.__class__.filter_defaults, filters)
            if include:
                params["include"] = include
        resp = self.client.session.get(url, params=params)
        resp = handle_response(resp).json()

        if included := resp.get("included"):
            for data in resp["data"]:
                for key, value in data["relationships"].items():
                    data["relationships"][key] = next(
                        (
                            include
                            for include in included
                            if include["type"] == value["data"]["type"]
                            and include["id"] == value["data"]["id"]
                        ),
                        None,
                    )

        return resp["data"]

    def post(self, attributes={}, relationships={}):
        json = self.parse_post_json(attributes, relationships)
        resp = self.client.session.post(self.url, json=json)
        return resp

    def patch(self, id, attributes={}, relationships={}):
        json = self.parse_patch_json(attributes, relationships, id=id)
        resp = self.client.session.patch(f"{self.url}/{id}", json=json)
        return resp

    def all(self, filters, include=None):
        # self.get but with different defaults
        raise NotImplementedError

    def parse_post_json(self, attributes, relationships) -> dict:
        cls = self.__class__
        return {
            "data": {
                "attributes": self._parsed_defaults(cls.attribute_defaults, attributes),
                "relationships": self._parsed_relationships(
                    cls.relationship_defaults, relationships
                ),
                "type": cls.resource_name,
            }
        }

    def parse_patch_json(self, *args, id):
        json = self.parse_post_json(*args)
        json["data"]["id"] = id
        return json

    def _id_to_relationship(self, id, resource_name):
        if not id:
            return {"data": None}
        return {
            "data": {
                "type": resource_name,
                "id": id,
            }
        }

    def _parsed_relationships(self, defaults: list[tuple], relationships: dict) -> dict:
        parsed = self._parsed_defaults(defaults, relationships)
        return {
            key: self._id_to_relationship(id, key + "s") for key, id in parsed.items()
        }

    def _parsed_value(self, value, type):
        if isinstance(value, datetime):
            value = value.strftime("%H:%M:%S")
        if isinstance(value, timedelta):
            value = serialize_duration(value)
        if isinstance(value, date):
            value = value.isoformat()
        return value if value != "user-id" else self.client.users.me["id"]

    def _parsed_defaults(self, defaults: list[tuple], values: dict) -> dict:
        return {
            default[0]: self._parsed_value(
                values.get(default[0]) or default[1],
                default[2] if len(default) > 2 else dict,
            )
            for default in defaults
        }

    @functools.cached_property
    def url(self):
        return self.client.url + self.__class__.resource_name


class Users(GetOnlyMixin, BaseModel):
    resource_name = "users"

    filter_defaults = [
        (
            "ordering",
            "username",
            str,
            "After what field should the users be ordered, can be 'email', 'username', 'first-name' or 'last-name'",
        ),
        ("active", None, bool, "Only active/inactive users."),
    ]

    @functools.cached_property
    def me(self):
        """Return the current logged in user."""
        return self.get(id="me")


class Reports(BaseModel):
    resource_name = "reports"

    attribute_defaults = [
        ("comment", None, str, "Comment -> what exactly did you work on"),
        ("date", date.today(), date, "Date of the report."),
        (
            "duration",
            timedelta(minutes=15),
            timedelta,
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

    def get(self, *args, raw=False, **kwargs):
        overtimes = super().get(*args, **kwargs)
        overtime = (
            [
                deserialize_duration(overtime["attributes"]["balance"])
                for overtime in overtimes
            ]
            if not raw and not kwargs.get("include")
            else overtimes
        )[0]
        return overtime


class Activity(BaseModel):
    resource_name = "activities"

    filter_defaults = [
        ("active", None, bool, "Is the activity currently active?"),
        ("day", date.today(), date, "The day/date if the Activity"),
    ]

    attribute_defaults = [
        ("comment", "", str, "The comment on the activity"),
        ("date", date.today(), date, "The date of the activity"),
        ("from-time", datetime.now(), datetime, "The beginning time of the activity."),
        ("to-time", None, datetime, "The end time of the activity."),
        ("review", False, bool, "Needs to be reviewed."),
        ("not-billable", False, bool, "Is not billable."),
    ]

    relationship_defaults = [
        ("task", None, "The id of the task of the activity"),
        ("user", "user-id", "The users id whoms't the activitty belongs to."),
    ]

    @property
    def current(self):
        return (self.get({"active": True}) or [[]])[0]

    def start(self, comment=""):
        if self.current:
            self.stop()
        return self.post({"comment": comment})

    def stop(self):
        if self.current:
            attributes = self.current["attributes"]
            attributes["to-time"] = datetime.now()
            r = self.patch(
                self.current["id"],
                attributes,
            )
            return r
