# -*- coding: utf-8 -*-
"""
In Jython 2.7b4 the clases `datetime.date`, `datetime.time` and `datetime.datetime` are
missing a __tojava__ method. This means that Django ORM's datetime objects are not
properly converted to a `java.sql.Date` object.

Refers to bug: http://bugs.jython.org/issue2271
"""


def install():
    from datetime import date, time, datetime

    from java.lang import Object
    from java.sql import Date, Timestamp, Time
    from java.util import Calendar
    from org.python.core import Py

    def date__tojava__(self, java_class):
        if java_class not in (Calendar, Date, Object):
            return Py.NoConversion

        calendar = Calendar.getInstance()
        calendar.clear()
        calendar.set(self.year, self.month - 1, self.day)
        if java_class == Calendar:
            return calendar
        else:
            return Date(calendar.getTimeInMillis())

    def time__tojava__(self, java_class):
        # TODO, if self.tzinfo is not None, convert time to UTC
        if java_class not in (Calendar, Time, Object):
            return Py.NoConversion

        calendar = Calendar.getInstance()
        calendar.clear()
        calendar.set(Calendar.HOUR_OF_DAY, self.hour)
        calendar.set(Calendar.MINUTE, self.minute)
        calendar.set(Calendar.SECOND, self.second)
        calendar.set(Calendar.MILLISECOND, self.microsecond // 1000)
        if java_class == Calendar:
            return calendar
        else:
            return Time(calendar.getTimeInMillis())

    def datetime__tojava__(self, java_class):
        # TODO, if self.tzinfo is not None, convert time to UTC
        if java_class not in (Calendar, Timestamp, Object):
            return Py.NoConversion

        calendar = Calendar.getInstance()
        calendar.clear()
        calendar.set(self.year, self.month - 1, self.day,
                     self.hour, self.minute, self.second)

        if java_class == Calendar:
            calendar.set(Calendar.MILLISECOND, self.microsecond // 1000)
            return calendar
        else:
            timestamp = Timestamp(calendar.getTimeInMillis())
            timestamp.setNanos(self.microsecond * 1000)
            return timestamp


    date.__tojava__ = date__tojava__
    time.__tojava__ = time__tojava__
    datetime.__tojava__ = datetime__tojava__