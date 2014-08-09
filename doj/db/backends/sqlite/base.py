# -*- coding: utf-8 -*-
"""
SQLite3 backend for DOJ.

Requires JDBC driver: org.sqlite.JDBC
"""

from __future__ import unicode_literals

import datetime
import warnings
import re

from django.conf import settings
from django.db import utils
from django.db.backends import utils as backend_utils
from django.db.models import fields
from django.db.models.sql import aggregates
from django.utils.dateparse import parse_date, parse_datetime, parse_time
from django.utils.encoding import force_text
from django.utils.functional import cached_property
from django.utils import six
from django.utils import timezone

from doj.db.backends import JDBCBaseDatabaseWrapper as BaseDatabaseWrapper
from doj.db.backends import JDBCBaseDatabaseFeatures as BaseDatabaseFeatures
from doj.db.backends import JDBCBaseDatabaseValidation as BaseDatabaseValidation
from doj.db.backends import JDBCBaseDatabaseOperations as BaseDatabaseOperations
from doj.db.backends import JDBCCursorWrapper as CursorWrapper
from doj.db.backends import JDBCConnection

from doj.db.backends.sqlite.client import DatabaseClient
from doj.db.backends.sqlite.creation import DatabaseCreation
from doj.db.backends.sqlite.introspection import DatabaseIntrospection
from doj.db.backends.sqlite.schema import DatabaseSchemaEditor

try:
    import pytz
except ImportError:
    pytz = None

DatabaseError = BaseDatabaseWrapper.DatabaseError
IntegrityError = BaseDatabaseWrapper.IntegrityError


def parse_datetime_with_timezone_support(value):
    dt = parse_datetime(value)
    # Confirm that dt is naive before overwriting its tzinfo.
    if dt is not None and settings.USE_TZ and timezone.is_naive(dt):
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def adapt_datetime_with_timezone_support(value):
    # Equivalent to DateTimeField.get_db_prep_value. Used only by raw SQL.
    if settings.USE_TZ:
        if timezone.is_naive(value):
            warnings.warn("SQLite received a naive datetime (%s)"
                          " while time zone support is active." % value,
                          RuntimeWarning)
            default_timezone = timezone.get_default_timezone()
            value = timezone.make_aware(value, default_timezone)
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.isoformat(str(" "))


def decoder(conv_func):
    """ The Python sqlite3 interface returns always byte strings.
        This function converts the received value to a regular string before
        passing it to the receiver function.
    """
    return lambda s: conv_func(s.decode('utf-8'))


def create_function(conn, name, num_args, py_func):
    from org.sqlite import Function
    class func(Function):
        def xFunc(self):
            assert self.super__args() == num_args
            args = [self.super__value_text(n) for n in xrange(0, num_args)]
            ret = py_func(*args)
            self.super__result(ret)
    Function.create(conn, name, func())


class SQLiteCursorWrapper(CursorWrapper):
    def close(self):
        try:
            return self.cursor.close()
        except BaseDatabaseWrapper.Database.ProgrammingError:
            pass


class DatabaseFeatures(BaseDatabaseFeatures):
    # SQLite cannot handle us only partially reading from a cursor's result set
    # and then writing the same rows to the database in another cursor. This
    # setting ensures we always read result sets fully into memory all in one
    # go.
    can_use_chunked_reads = False
    test_db_allows_multiple_connections = False
    supports_unspecified_pk = True
    supports_timezones = False
    supports_1000_query_parameters = False
    supports_mixed_date_datetime_comparisons = False
    has_bulk_insert = True
    can_combine_inserts_with_and_without_auto_increment_pk = False
    supports_foreign_keys = False
    supports_column_check_constraints = False
    autocommits_when_autocommit_is_off = True
    can_introspect_decimal_field = False
    can_introspect_positive_integer_field = True
    can_introspect_small_integer_field = True
    supports_transactions = True
    atomic_transactions = False
    can_rollback_ddl = True
    supports_paramstyle_pyformat = False
    supports_sequence_reset = False

    @cached_property
    def uses_savepoints(self):
        with self.connection.cursor() as cursor:
            cursor.execute('SELECT SQLITE_VERSION()')
            version = (int(i) for i in cursor.fetchone()[0].split('.'))
            return version >= (3, 6, 8, 0)

    @cached_property
    def supports_stddev(self):
        """
        Confirm support for STDDEV and related stats functions

        SQLite supports STDDEV as an extension package; so
        connection.ops.check_aggregate_support() can't unilaterally
        rule out support for STDDEV. We need to manually check
        whether the call works.
        """
        with self.connection.cursor() as cursor:
            cursor.execute('CREATE TABLE STDDEV_TEST (X INT)')
            try:
                cursor.execute('SELECT STDDEV(*) FROM STDDEV_TEST')
                has_support = True
            except utils.DatabaseError:
                has_support = False
            cursor.execute('DROP TABLE STDDEV_TEST')
        return has_support

    @cached_property
    def has_zoneinfo_database(self):
        return pytz is not None


class DatabaseOperations(BaseDatabaseOperations):
    def bulk_batch_size(self, fields, objs):
        """
        SQLite has a compile-time default (SQLITE_LIMIT_VARIABLE_NUMBER) of
        999 variables per query.

        If there is just single field to insert, then we can hit another
        limit, SQLITE_MAX_COMPOUND_SELECT which defaults to 500.
        """
        limit = 999 if len(fields) > 1 else 500
        return (limit // len(fields)) if len(fields) > 0 else len(objs)

    def check_aggregate_support(self, aggregate):
        bad_fields = (fields.DateField, fields.DateTimeField, fields.TimeField)
        bad_aggregates = (aggregates.Sum, aggregates.Avg,
                          aggregates.Variance, aggregates.StdDev)
        if (isinstance(aggregate.source, bad_fields) and
                isinstance(aggregate, bad_aggregates)):
            raise NotImplementedError(
                'You cannot use Sum, Avg, StdDev and Variance aggregations '
                'on date/time fields in sqlite3 '
                'since date/time is saved as text.')

    def date_extract_sql(self, lookup_type, field_name):
        # sqlite doesn't support extract, so we fake it with the user-defined
        # function django_date_extract that's registered in connect(). Note that
        # single quotes are used because this is a string (and could otherwise
        # cause a collision with a field name).
        return "django_date_extract('%s', %s)" % (lookup_type.lower(), field_name)

    def date_interval_sql(self, sql, connector, timedelta):
        # It would be more straightforward if we could use the sqlite strftime
        # function, but it does not allow for keeping six digits of fractional
        # second information, nor does it allow for formatting date and datetime
        # values differently. So instead we register our own function that
        # formats the datetime combined with the delta in a manner suitable
        # for comparisons.
        return 'django_format_dtdelta(%s, "%s", "%d", "%d", "%d")' % (sql,
            connector, timedelta.days, timedelta.seconds, timedelta.microseconds)

    def date_trunc_sql(self, lookup_type, field_name):
        # sqlite doesn't support DATE_TRUNC, so we fake it with a user-defined
        # function django_date_trunc that's registered in connect(). Note that
        # single quotes are used because this is a string (and could otherwise
        # cause a collision with a field name).
        return "django_date_trunc('%s', %s)" % (lookup_type.lower(), field_name)

    def datetime_extract_sql(self, lookup_type, field_name, tzname):
        # Same comment as in date_extract_sql.
        if settings.USE_TZ:
            if pytz is None:
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured("This query requires pytz, "
                                           "but it isn't installed.")
        return "django_datetime_extract('%s', %s, %%s)" % (
            lookup_type.lower(), field_name), [tzname]

    def datetime_trunc_sql(self, lookup_type, field_name, tzname):
        # Same comment as in date_trunc_sql.
        if settings.USE_TZ:
            if pytz is None:
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured("This query requires pytz, "
                                           "but it isn't installed.")
        return "django_datetime_trunc('%s', %s, %%s)" % (
            lookup_type.lower(), field_name), [tzname]

    def drop_foreignkey_sql(self):
        return ""

    def pk_default_value(self):
        return "NULL"

    def quote_name(self, name):
        if name.startswith('"') and name.endswith('"'):
            return name  # Quoting once is enough.
        return '"%s"' % name

    def no_limit_value(self):
        return -1

    def sql_flush(self, style, tables, sequences, allow_cascade=False):
        # NB: The generated SQL below is specific to SQLite
        # Note: The DELETE FROM... SQL generated below works for SQLite databases
        # because constraints don't exist
        sql = ['%s %s %s;' % (
            style.SQL_KEYWORD('DELETE'),
            style.SQL_KEYWORD('FROM'),
            style.SQL_FIELD(self.quote_name(table))
        ) for table in tables]
        # Note: No requirement for reset of auto-incremented indices (cf. other
        # sql_flush() implementations). Just return SQL at this point
        return sql

    def value_to_db_datetime(self, value):
        if value is None:
            return None

        # SQLite doesn't support tz-aware datetimes
        if timezone.is_aware(value):
            if settings.USE_TZ:
                value = value.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                raise ValueError("SQLite backend does not support timezone-aware datetimes when USE_TZ is False.")

        return six.text_type(value)

    def value_to_db_time(self, value):
        if value is None:
            return None

        # SQLite doesn't support tz-aware datetimes
        if timezone.is_aware(value):
            raise ValueError("SQLite backend does not support timezone-aware times.")

        return six.text_type(value)

    def convert_values(self, value, field):
        """
        SQLite returns floats when it should be returning decimals,
        and gets dates and datetimes wrong.
        For consistency with other backends, coerce when required.
        """
        if value is None:
            return None

        internal_type = field.get_internal_type()
        if internal_type == 'DecimalField':
            return backend_utils.typecast_decimal(field.format_number(value))
        elif internal_type and internal_type.endswith('IntegerField') or internal_type == 'AutoField':
            return int(value)
        elif internal_type == 'DateField':
            return parse_date(value)
        elif internal_type == 'DateTimeField':
            return parse_datetime_with_timezone_support(value)
        elif internal_type == 'TimeField':
            return parse_time(value)

        # No field, or the field isn't known to be a decimal or integer
        return value

    def bulk_insert_sql(self, fields, num_values):
        res = []
        res.append("SELECT %s" % ", ".join(
            "%%s AS %s" % self.quote_name(f.column) for f in fields
        ))
        res.extend(["UNION ALL SELECT %s" % ", ".join(["%s"] * len(fields))] * (num_values - 1))
        return " ".join(res)

    def combine_expression(self, connector, sub_expressions):
        # SQLite doesn't have a power function, so we fake it with a
        # user-defined function django_power that's registered in connect().
        if connector == '^':
            return 'django_power(%s)' % ','.join(sub_expressions)
        return super(DatabaseOperations, self).combine_expression(connector, sub_expressions)

    def integer_field_range(self, internal_type):
        # SQLite doesn't enforce any integer constraints
        return (None, None)

    def last_insert_id(self, cursor, table_name, pk_name):
        cursor.execute("SELECT LAST_INSERT_ROWID()")
        return cursor.fetchone()[0]


class DatabaseWrapper(BaseDatabaseWrapper):
    vendor = 'sqlite'
    jdbc_driver_class_name = 'org.sqlite.JDBC'
    jdbc_connection_url_pattern = 'jdbc:sqlite://%(NAME)s'
    jdbc_default_host = ''
    jdbc_default_port = 0
    jdbc_default_name = ':memory:'
    # SQLite requires LIKE statements to include an ESCAPE clause if the value
    # being escaped has a percent or underscore in it.
    # See http://www.sqlite.org/lang_expr.html for an explanation.
    operators = {
        'exact': '= %s',
        'iexact': "LIKE %s ESCAPE '\\'",
        'contains': "LIKE %s ESCAPE '\\'",
        'icontains': "LIKE %s ESCAPE '\\'",
        'regex': 'REGEXP %s',
        'iregex': "REGEXP '(?i)' || %s",
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': "LIKE %s ESCAPE '\\'",
        'endswith': "LIKE %s ESCAPE '\\'",
        'istartswith': "LIKE %s ESCAPE '\\'",
        'iendswith': "LIKE %s ESCAPE '\\'",
    }

    pattern_ops = {
        'startswith': "LIKE %s || '%%%%'",
        'istartswith': "LIKE UPPER(%s) || '%%%%'",
    }

    class Database(BaseDatabaseWrapper.Database):

        @staticmethod
        def Binary(value):
            """
            The SQLite JDBC driver does not support binary fields,
            so we use them as text fields.
            """
            return bytes(value)

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation(self)

    def get_new_connection(self, conn_params):
        conn = super(DatabaseWrapper, self).get_new_connection(conn_params)
        create_function(conn.__connection__, "django_date_extract", 2, _sqlite_date_extract)
        create_function(conn.__connection__, "django_date_trunc", 2, _sqlite_date_trunc)
        create_function(conn.__connection__, "django_datetime_extract", 3, _sqlite_datetime_extract)
        create_function(conn.__connection__, "django_datetime_trunc", 3, _sqlite_datetime_trunc)
        create_function(conn.__connection__, "regexp", 2, _sqlite_regexp)
        create_function(conn.__connection__, "django_format_dtdelta", 5, _sqlite_format_dtdelta)
        create_function(conn.__connection__, "django_power", 2, _sqlite_power)
        return conn

    def init_connection_state(self):
        pass

    def create_cursor(self):
        return SQLiteCursorWrapper(self.connection.cursor())

    def close(self):
        self.validate_thread_sharing()
        # If database is in memory, closing the connection destroys the
        # database. To prevent accidental data loss, ignore close requests on
        # an in-memory db.
        if self.settings_dict['NAME'] != ":memory:":
            BaseDatabaseWrapper.close(self)

    def _savepoint_allowed(self):
        # Two conditions are required here:
        # - A sufficiently recent version of SQLite to support savepoints,
        # - Being in a transaction, which can only happen inside 'atomic'.

        # When 'isolation_level' is not None, sqlite3 commits before each
        # savepoint; it's a bug. When it is None, savepoints don't make sense
        # because autocommit is enabled. The only exception is inside 'atomic'
        # blocks. To work around that bug, on SQLite, 'atomic' starts a
        # transaction explicitly rather than simply disable autocommit.
        return self.features.uses_savepoints and self.in_atomic_block


    def _commit(self):
        if self.connection is not None and not self.connection.autocommit:
            with self.wrap_database_errors:
                return self.connection.commit()

    def check_constraints(self, table_names=None):
        """
        Checks each table name in `table_names` for rows with invalid foreign key references. This method is
        intended to be used in conjunction with `disable_constraint_checking()` and `enable_constraint_checking()`, to
        determine if rows with invalid references were entered while constraint checks were off.

        Raises an IntegrityError on the first invalid foreign key reference encountered (if any) and provides
        detailed information about the invalid reference in the error message.

        Backends can override this method if they can more directly apply constraint checking (e.g. via "SET CONSTRAINTS
        ALL IMMEDIATE")
        """
        cursor = self.cursor()
        if table_names is None:
            table_names = self.introspection.table_names(cursor)
        for table_name in table_names:
            primary_key_column_name = self.introspection.get_primary_key_column(cursor, table_name)
            if not primary_key_column_name:
                continue
            key_columns = self.introspection.get_key_columns(cursor, table_name)
            for column_name, referenced_table_name, referenced_column_name in key_columns:
                cursor.execute("""
                    SELECT REFERRING.`%s`, REFERRING.`%s` FROM `%s` as REFERRING
                    LEFT JOIN `%s` as REFERRED
                    ON (REFERRING.`%s` = REFERRED.`%s`)
                    WHERE REFERRING.`%s` IS NOT NULL AND REFERRED.`%s` IS NULL"""
                    % (primary_key_column_name, column_name, table_name, referenced_table_name,
                    column_name, referenced_column_name, column_name, referenced_column_name))
                for bad_row in cursor.fetchall():
                    raise utils.IntegrityError("The row in table '%s' with primary key '%s' has an invalid "
                        "foreign key: %s.%s contains a value '%s' that does not have a corresponding value in %s.%s."
                        % (table_name, bad_row[0], table_name, column_name, bad_row[1],
                        referenced_table_name, referenced_column_name))

    def is_usable(self):
        return True

    def _start_transaction_under_autocommit(self):
        pass

    def schema_editor(self, *args, **kwargs):
        """
        Returns a new instance of this backend's SchemaEditor
        """
        return DatabaseSchemaEditor(self, *args, **kwargs)

    @staticmethod
    def _set_default_isolation_level(connection):
        """
        Make transactions transparent to all cursors. Must be called by zxJDBC backends
        after instantiating a connection.

        :param connection: zxJDBC connection
        """
        jdbc_connection = connection.__connection__
        jdbc_connection.setTransactionIsolation(JDBCConnection.TRANSACTION_SERIALIZABLE)


def _sqlite_date_extract(lookup_type, dt):
    if dt is None:
        return None
    try:
        if str(dt).isdecimal():
            dt = datetime.datetime.fromtimestamp(int(dt)/1000)
        else:
            dt = backend_utils.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    if lookup_type == 'week_day':
        return (dt.isoweekday() % 7) + 1
    else:
        return getattr(dt, lookup_type)


def _sqlite_date_trunc(lookup_type, dt):
    try:
        if str(dt).isdecimal():
            dt = datetime.datetime.fromtimestamp(int(dt)/1000)
        else:
            dt = backend_utils.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    if lookup_type == 'year':
        return "%i-01-01" % dt.year
    elif lookup_type == 'month':
        return "%i-%02i-01" % (dt.year, dt.month)
    elif lookup_type == 'day':
        return "%i-%02i-%02i" % (dt.year, dt.month, dt.day)


def _sqlite_datetime_extract(lookup_type, dt, tzname):
    if dt is None:
        return None
    try:
        if str(dt).isdecimal():
            dt = datetime.datetime.fromtimestamp(int(dt)/1000)
        else:
            dt = backend_utils.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    if tzname is not None:
        dt = timezone.localtime(dt, pytz.timezone(tzname))
    if lookup_type == 'week_day':
        return (dt.isoweekday() % 7) + 1
    else:
        return getattr(dt, lookup_type)


def _sqlite_datetime_trunc(lookup_type, dt, tzname):
    try:
        if str(dt).isdecimal():
            dt = datetime.datetime.fromtimestamp(int(dt)/1000)
        else:
            dt = backend_utils.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    if tzname is not None:
        dt = timezone.localtime(dt, pytz.timezone(tzname))
    if lookup_type == 'year':
        return "%i-01-01 00:00:00" % dt.year
    elif lookup_type == 'month':
        return "%i-%02i-01 00:00:00" % (dt.year, dt.month)
    elif lookup_type == 'day':
        return "%i-%02i-%02i 00:00:00" % (dt.year, dt.month, dt.day)
    elif lookup_type == 'hour':
        return "%i-%02i-%02i %02i:00:00" % (dt.year, dt.month, dt.day, dt.hour)
    elif lookup_type == 'minute':
        return "%i-%02i-%02i %02i:%02i:00" % (dt.year, dt.month, dt.day, dt.hour, dt.minute)
    elif lookup_type == 'second':
        return "%i-%02i-%02i %02i:%02i:%02i" % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)


def _sqlite_format_dtdelta(dt, conn, days, secs, usecs):
    try:
        if str(dt).isdecimal():
            dt = datetime.datetime.fromtimestamp(int(dt)/1000)
        else:
            dt = backend_utils.typecast_timestamp(dt)
        delta = datetime.timedelta(int(days), int(secs), int(usecs))
        if conn.strip() == '+':
            dt = dt + delta
        else:
            dt = dt - delta
    except (ValueError, TypeError):
        return None
    # typecast_timestamp returns a date or a datetime without timezone.
    # It will be formatted as "%Y-%m-%d" or "%Y-%m-%d %H:%M:%S[.%f]"
    return str(dt)


def _sqlite_regexp(re_pattern, re_string):
    return bool(re.search(re_pattern, force_text(re_string))) if re_string is not None else False


def _sqlite_power(x, y):
    return x ** y
