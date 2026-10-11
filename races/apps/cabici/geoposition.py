#!/usr/bin/python
#
# Copyright 2025 Steve Cassidy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A minimal latitude/longitude model field.

Replaces the unmaintained ``django-geoposition`` package. The database
representation is unchanged (a ``"lat,long"`` string in a ``varchar(42)``) so
no data migration is required.
"""

from decimal import Decimal, InvalidOperation

from django import forms
from django.db import models
from django.utils.translation import gettext_lazy as _

__all__ = ("Geoposition", "GeopositionField", "GeopositionFormField", "GeopositionWidget")


class Geoposition:
    """Immutable latitude/longitude value object.

    Values are stored as ``Decimal`` and serialise to the historic
    ``"lat,long"`` string form.
    """

    __slots__ = ("latitude", "longitude")

    def __init__(self, latitude, longitude):
        try:
            self.latitude = Decimal(latitude)
            self.longitude = Decimal(longitude)
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid geoposition: {latitude!r}, {longitude!r}") from exc

    def __str__(self):
        return f"{self.latitude},{self.longitude}"

    def __repr__(self):
        return f"Geoposition({self})"

    def __len__(self):
        return len(str(self))

    def __eq__(self, other):
        if not isinstance(other, Geoposition):
            return NotImplemented
        return self.latitude == other.latitude and self.longitude == other.longitude

    def __hash__(self):
        return hash((self.latitude, self.longitude))

    def as_tuple(self):
        """Return the position as a ``(latitude, longitude)`` decimal pair."""
        return (self.latitude, self.longitude)


class _Missing:
    def __repr__(self):
        return "<missing>"


_MISSING = _Missing()


class GeopositionDescriptor:
    """Coerce values assigned to a ``GeopositionField`` attribute.

    Django only runs ``from_db_value`` for values loaded from the database, so
    without this descriptor an in-memory instance would hold the raw string
    while a reloaded instance would hold a :class:`Geoposition`.
    """

    def __init__(self, field):
        self.field = field
        self.attname = field.attname

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        value = instance.__dict__.get(self.attname, _MISSING)
        if value is _MISSING:
            return None
        if isinstance(value, models.Field):
            # The field was deferred by a queryset; fetch it now.
            instance.refresh_from_db(fields=[self.attname])
            value = instance.__dict__.get(self.attname)
        return self.field.to_python(value)

    def __set__(self, instance, value):
        instance.__dict__[self.attname] = self.field.to_python(value)


class GeopositionWidget(forms.MultiWidget):
    """Two text inputs for latitude and longitude."""

    def decompress(self, value):
        try:
            position = GeopositionField().to_python(value)
        except ValueError:
            return [None, None]
        if position is None:
            return [None, None]
        return [position.latitude, position.longitude]


class GeopositionFormField(forms.MultiValueField):
    widget = GeopositionWidget
    default_error_messages = {
        "invalid": _("Enter a valid geoposition."),
        "out_of_range": _("Latitude must be between -90 and 90, longitude between -180 and 180."),
    }

    def __init__(self, *args, **kwargs):
        fields = (
            forms.DecimalField(label=_("Latitude")),
            forms.DecimalField(label=_("Longitude")),
        )
        required = kwargs.pop("required", True)
        fields[0].required = fields[1].required = required
        super().__init__(fields, *args, **kwargs)

    def compress(self, value_list):
        if not value_list:
            return None
        if any(value is None or value == "" for value in value_list):
            raise forms.ValidationError(self.error_messages["invalid"], code="invalid")
        position = Geoposition(*value_list)
        if not (-90 <= position.latitude <= 90) or not (-180 <= position.longitude <= 180):
            raise forms.ValidationError(self.error_messages["out_of_range"], code="out_of_range")
        return position


class GeopositionField(models.Field):
    """Model field storing a :class:`Geoposition` as a ``"lat,long"`` string."""

    description = _("A geoposition (latitude and longitude)")

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 42
        super().__init__(*args, **kwargs)

    def get_internal_type(self):
        return "CharField"

    def contribute_to_class(self, cls, name, private_only=False):
        super().contribute_to_class(cls, name, private_only=private_only)
        setattr(cls, self.attname, GeopositionDescriptor(self))

    def to_python(self, value):
        if value is None or value == "" or value == "None":
            return None
        if isinstance(value, Geoposition):
            return value
        if isinstance(value, (list, tuple)):
            return Geoposition(*value)
        if isinstance(value, dict):
            return Geoposition(value.get("lat"), value.get("lon"))

        parts = str(value).rsplit(",", 1)
        if len(parts) != 2:
            raise ValueError("Geoposition values must be in 'lat,long' form: %r" % value)
        return Geoposition(*parts)

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def get_prep_value(self, value):
        position = self.to_python(value)
        if position is None:
            # Historic behaviour: a non-nullable column holds the empty string
            # rather than NULL.
            return None if self.null else ""
        return str(position)

    def value_to_string(self, obj):
        position = self.value_from_object(obj)
        return "" if position is None else str(position)

    def formfield(self, **kwargs):
        defaults = {"form_class": GeopositionFormField}
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # Keep the database representation identical to the historical package.
        kwargs["max_length"] = 42
        return name, path, args, kwargs
