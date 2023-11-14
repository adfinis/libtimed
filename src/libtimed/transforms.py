from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from enum import Enum as EnumClass

TIME_FORMAT = "%H:%M:%S"


class SerializationError(ValueError):

    """Error raised only inside of Transforms when trying to (de)serialize values."""


class BaseTransform:

    """Base class for serializers."""

    @staticmethod
    def serialize(value_for_api):
        """Serialize a value so that it can be sent to the API."""
        return value_for_api

    @staticmethod
    def deserialize(value_from_api):
        """Deserialize a value from the API so that it can be used in a pythonic way."""
        return value_from_api


class Type(BaseTransform):

    """Transform for types."""

    def __init__(
        self, type: type, allow_none: bool = True, pipe: Callable = lambda x: x
    ):
        self.type = type
        self.pipe = pipe
        self.allow_none = allow_none

    def _validate(self, value):
        if not isinstance(value, self.type) and not (value is None and self.allow_none):
            raise SerializationError(
                f"The provided value ({value}) is not of type {self.type} but instead of type {type(self.type)}"
            )
        return value

    def serialize(self, value, **_):
        return self.pipe(self._validate(value))

    def deserialize(self, value):
        return self.pipe(self._validate(value))


class Duration(BaseTransform):

    """Transform for durations."""

    @staticmethod
    def serialize(duration: timedelta | str, **_) -> str:
        if isinstance(duration, str):
            # validate by calling deserialize on it
            return duration

        Type(timedelta, False).serialize(duration)
        days = ""
        if duration.days != 0:
            days = str(duration.days) + " "
        hours, minutes, seconds = str(duration).split(" ")[-1].split(":")
        return f"{days}{hours.zfill(2)}:{minutes}:{seconds}"

    @staticmethod
    def deserialize(duration: str) -> timedelta:
        # TODO: add validation
        days = 0
        if len(duration.split(" ")) != 1:
            days, duration = duration.split(" ")
        hours, minutes, seconds = map(int, duration.split(":"))
        return timedelta(days=int(days), hours=hours, minutes=minutes, seconds=seconds)


class RelationShipProperty:
    def __init__(self, property_name) -> None:
        self.property_name = property_name


class Relationship(BaseTransform):

    """Transform for relationships. This is very hacky and should be replaced with a better solution."""

    def __init__(self, related_model) -> None:
        self.related_model = related_model

    def serialize(
        self,
        value: int | str | RelationShipProperty | None,
        is_filter=False,
        client=None,
    ) -> dict | str | None:
        if not value:
            return {"data": None}
        if isinstance(value, dict):
            return value
        data = {}
        if isinstance(value, RelationShipProperty):
            if not client:
                raise SerializationError(
                    "Client has to be passed when using a property"
                )
            try:
                data["data"] = getattr(self.related_model(client), value.property_name)
            except AttributeError as e:
                raise SerializationError(
                    f"Unknown property {value} on {self.related_model}!"
                ) from e
        return_value: dict = data or {
            "data": {"type": self.related_model.resource_name, "id": data or value}
        }
        return return_value["data"].get("id") if is_filter else return_value

    def deserialize(self, value: dict) -> dict | None:
        data = value.get("data") or {}
        if (
            recieved_type := (data or {}).get("type")
        ) != self.related_model.resource_name:
            if recieved_type is None:
                return None
            raise SerializationError(
                f"Recieved realtionship of type ({recieved_type}), expected type ({self.related_model.resource_name}"
            )
        return data


class Date(BaseTransform):

    """Transform for dates."""

    @staticmethod
    def serialize(value: date | str, **_) -> str:
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value).date()
            except ValueError as e:
                raise SerializationError(
                    f"The provided value ({value}) is not formatted correctly."
                ) from e
        return value if value is None else value.isoformat()

    @staticmethod
    def deserialize(value_from_api) -> date:
        return datetime.strptime(value_from_api, "%Y-%m-%d").date()


class Time(BaseTransform):

    """Transform for times."""

    def __init__(self, return_datetime: bool = False):
        # return_datetime will be removed at some point
        # it defaults to True to maintain backwards compatibility
        self.return_datetime = return_datetime

    def _return_value(self, value: datetime):
        if self.return_datetime:
            return value
        return value.time()

    def serialize(self, value: time | str, **_) -> str | None:
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, TIME_FORMAT).time()
            except ValueError as e:
                raise SerializationError(
                    f"The provided value ({value}) is not formatted correctly ({TIME_FORMAT})."
                ) from e

        return value.strftime(TIME_FORMAT) if value else None

    def deserialize(self, value) -> time | datetime | None:
        return (
            self._return_value(datetime.strptime(value, "%H:%M:%S")) if value else None
        )


class Enum(BaseTransform):
    def __init__(self, enum: type[EnumClass]) -> None:
        self.enum = enum

    def serialize(self, value, **_):
        value = value if isinstance(value, str) else value.value
        if value not in self.enum._value2member_map_:
            raise SerializationError(
                f"The provided value ({value}) is not an option, consider using {self.enum.__name__}.{{{','.join(self.enum.__members__)}}}."
            )

    def deserialize(self, value):
        if value not in self.enum._value2member_map_:
            raise SerializationError(
                f"The value ({value}) provided by the API is not a member of {self.enum.__name__}, options are: {self.enum.__name__}.{{{','.join(self.enum.__members__)}}}."
            )
