import functools
from datetime import date, datetime, timedelta
from enum import Enum

from inflection import underscore
from requests import Response

from libtimed import transforms

DATE = ("date", date.today(), transforms.Date)
FROM_DATE = ("from_date", None, transforms.Date)
TO_DATE = ("to_date", None, transforms.Date)
DURATION = ("duration", timedelta(minutes=15), transforms.Duration)
COMMENT = ("comment", "", transforms.Type(str, False))
REVIEW = ("review", False, transforms.Type(bool, False))
NOT_BILLABLE = ("not-billable", False, transforms.Type(bool, False))
NAME = ("name", None, transforms.Type(str))


class UserOrdering(Enum):
    EMAIL = "email"
    FIRST_NAME = "first-name"
    LAST_NAME = "last_name"
    USERNAME = "username"


class GetOnlyMixin:
    message = "This model is get-only!"

    def post(self, *args, **kwargs) -> None:
        raise NotImplementedError(self.__class__.message)

    def patch(self, *args, **kwargs) -> None:
        raise NotImplementedError(self.__class__.message)


class BaseModel:
    def __init__(self, client) -> None:
        self.client = client

    attributes: list[tuple]
    relationships: list[tuple]
    filters: list[tuple]

    def get(self, filters={}, include=None, id=None, raw=False) -> dict:
        url = f"{self.url}/{id}" if id else self.url
        if id:
            params = include
        else:
            params = self._parse_filters(filters)
            if include:
                params["include"] = include
                # TODO: map included resources to relationships
                raw = True

        resp = self.client.session.get(url, params=params)
        resp = resp.json()

        # de-serialize
        if data := ([resp.get("data")] if id else resp.get("data")):
            for item in data:
                for key, value in item["attributes"].items():
                    transform = next(
                        (
                            transform
                            for name, _, transform in self.__class__.attributes
                            if name == key
                        ),
                        None,
                    )
                    item["attributes"][key] = (
                        (transform).deserialize(value) if transform else value
                    )
                relationships = item.get("relationships")
                if not relationships:
                    continue
                for key, value in relationships.items():
                    related_model = next(
                        (
                            related_model
                            for name, _, related_model, in self.__class__.relationships
                            if name == key
                        ),
                        None,
                    )
                    item["relationships"][key] = (
                        transforms.Relationship(related_model).deserialize(value)
                        if related_model
                        else value
                    )
        return resp if raw else resp.get("data")

    def post(self, attributes={}, relationships={}) -> Response:
        json = self._parse_post_json(attributes, relationships)
        resp = self.client.session.post(self.url, json=json)
        return resp

    def patch(self, id, attributes={}, relationships={}) -> Response:
        json = self._parse_post_json(attributes, relationships)
        json["data"]["id"] = id
        resp = self.client.session.patch(f"{self.url}/{id}", json=json)
        return resp

    def delete(self, id) -> Response:
        return self.client.session.delete(f"{self.url}/{id}")

    @classmethod
    @property
    def resource_name(cls):
        return underscore(cls.__name__).replace("_", "-")

    def _parse_post_json(self, attributes, relationships) -> dict:
        return {
            "data": {
                "attributes": self._parse_attributes(attributes),
                "relationships": self._parse_relationships(relationships),
                "type": self.resource_name,
            }
        }

    def _parse_attributes(self, passed_attributes: dict = {}):
        attributes = self.__class__.attributes

        return {
            name: (transform).serialize((passed_attributes.get(name) or value))
            for name, value, transform in attributes
        }

    def _parse_filters(self, passed_filters: dict = {}):
        filters = self.__class__.filters

        return {
            name: (transform).serialize(
                passed_filters.get(name) or value, is_filter=True, client=self.client
            )
            for name, value, transform in filters
        }

    def _parse_relationships(self, passed_relationships):
        relationships = self.__class__.relationships

        return {
            name: transforms.Relationship(related_model).serialize(
                passed_relationships.get(name) or value, client=self.client
            )
            for name, value, related_model in relationships
        }

    @functools.cached_property
    def url(self):
        return self.client.url + self.resource_name


class Users(GetOnlyMixin, BaseModel):
    filters = [
        ("ordering", UserOrdering.USERNAME, transforms.Enum(UserOrdering)),
        ("active", None, transforms.Type(bool)),
    ]

    attributes = []
    relationships = []

    @functools.cached_property
    def me(self):
        """Return the current logged in user."""
        return self.get(id="me")


CURRENT_USER_FILTER = (
    "user",
    transforms.RelationShipProperty("me"),
    transforms.Relationship(Users),
)
CURRENT_USER_RELATIONSHIP = ("user", transforms.RelationShipProperty("me"), Users)


class WorktimeBalances(
    GetOnlyMixin,
    BaseModel,
):
    filters = [CURRENT_USER_FILTER, DATE, FROM_DATE, TO_DATE]
    attributes = [DATE, ("balance", None, transforms.Duration)]
    relationships = [("user", None, Users)]

    def get(self, *args, **kwargs):
        overtimes = super().get(*args, **kwargs)
        return (
            overtimes
            if (kwargs.get("raw") or kwargs.get("include"))
            else overtimes[0]["attributes"]["balance"]
        )


class Customers(GetOnlyMixin, BaseModel):
    filters = [("archived", None, transforms.Type(bool))]
    attributes = [NAME, ("archived", False, transforms.Type(bool, False))]
    relationships = []


class Projects(GetOnlyMixin, BaseModel):
    filters = [("customer", None, transforms.Relationship(Customers))]
    attributes = [NAME]
    relationships = [("customer", None, Customers)]


class Tasks(GetOnlyMixin, BaseModel):
    filters = [("project", None, transforms.Relationship(Projects))]
    attributes = [NAME]
    relationships = [("project", None, Projects)]


class Activities(BaseModel):
    filters = [
        ("active", None, transforms.Type(bool)),
        ("day", date.today(), transforms.Date),
    ]

    attributes = [
        ("from-time", datetime.now(), transforms.Time),
        ("to-time", None, transforms.Time),
        COMMENT,
        DATE,
        REVIEW,
        NOT_BILLABLE,
    ]

    relationships = [
        CURRENT_USER_RELATIONSHIP,
        ("task", None, Tasks),
    ]

    @property
    def current(self):
        return (self.get({"active": True}) or [{}])[0]

    def start(self, **kwargs):
        if self.current:
            self.stop()
        return self.post(**kwargs)

    def stop(self):
        if self.current:
            attributes = self.current["attributes"]
            attributes["to-time"] = datetime.now()
            r = self.patch(
                self.current["id"],
                attributes,
            )
            return r


class Reports(BaseModel):
    attributes = [COMMENT, DATE, DURATION, REVIEW, NOT_BILLABLE]

    relationships = [CURRENT_USER_RELATIONSHIP, ("task", None, Tasks)]

    filters = [CURRENT_USER_FILTER, DATE, FROM_DATE, TO_DATE]
