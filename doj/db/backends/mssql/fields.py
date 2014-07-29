"""This module provides SQL Server specific fields for Django models."""
from __future__ import unicode_literals
import datetime
from django.db import models
from django.forms import ValidationError
from django.utils import six, timezone
from django.utils.translation import ugettext_lazy as _

if six.PY3:
    long = int

__all__ = (
    'BigAutoField',
    'BigForeignKey',
    'BigIntegerField',
    'DateField',
    'DateTimeField',
    'DateTimeOffsetField',
    'LegacyTimeField',
    'LegacyDateField',
    'LegacyDateTimeField',
    'TimeField',
)


class BigAutoField(models.AutoField):
    """A bigint IDENTITY field"""
    def get_internal_type(self):
        return "BigAutoField"

    def to_python(self, value):
        if value is None:
            return value
        try:
            return long(value)
        except (TypeError, ValueError):
            raise ValidationError(
                _("This value must be a long."))

    def get_db_prep_value(self, value, connection=None, prepared=False):
        if value is None:
            return None
        return long(value)


class BigForeignKey(models.ForeignKey):
    """A ForeignKey field that points to a BigAutoField or BigIntegerField"""
    def db_type(self, connection=None):
        try:
            return models.BigIntegerField().db_type(connection=connection)
        except AttributeError:
            return models.BigIntegerField().db_type()

BigIntegerField = models.BigIntegerField


def convert_microsoft_date_to_isoformat(value):
    if isinstance(value, six.string_types):
        value = value.replace(' +', '+').replace(' -', '-')
    return value


class DateField(models.DateField):
    """
    A DateField backed by a 'date' database field.
    """
    def get_internal_type(self):
        return 'NewDateField'

    def to_python(self, value):
        val = super(DateField, self).to_python(
            convert_microsoft_date_to_isoformat(value)
        )
        if isinstance(val, datetime.datetime):
            val = datetime.date()
        return val


class DateTimeField(models.DateTimeField):
    """
    A DateTimeField backed by a 'datetime2' database field.
    """
    def get_internal_type(self):
        return 'NewDateTimeField'

    def to_python(self, value):
        from django.conf import settings
        result = super(DateTimeField, self).to_python(
            convert_microsoft_date_to_isoformat(value)
        )
        if result:
            if timezone.is_aware(result) and not settings.USE_TZ:
                result = timezone.make_naive(result, timezone.utc)
            elif settings.USE_TZ:
                result = timezone.make_aware(result, timezone.utc)
        return result

    def get_db_prep_value(self, value, connection, prepared=False):
        if not prepared:
            value = self.get_prep_value(value)
        return connection.ops._new_value_to_db_datetime(value)


class DateTimeOffsetField(models.DateTimeField):
    """
    A DateTimeOffsetField backed by a 'datetimeoffset' database field.
    """
    def get_internal_type(self):
        return 'DateTimeOffsetField'

    def to_python(self, value):
        return super(DateTimeOffsetField, self).to_python(
            convert_microsoft_date_to_isoformat(value)
        )

    def get_db_prep_value(self, value, connection, prepared=False):
        if not prepared:
            value = self.get_prep_value(value)
        if value is None:
            return None
        return value.isoformat()


class TimeField(models.TimeField):
    """
    A TimeField backed by a 'time' database field.
    """
    def get_internal_type(self):
        return 'NewTimeField'

    def to_python(self, value):
        return super(TimeField, self).to_python(
            convert_microsoft_date_to_isoformat(value)
        )

    def get_db_prep_value(self, value, connection, prepared=False):
        if not prepared:
            value = self.get_prep_value(value)
        return connection.ops._new_value_to_db_time(value)