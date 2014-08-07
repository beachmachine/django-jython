# -*- coding: utf-8 -*-
"""
MySQL database backend for DOJ.

Requires JDBC driver: com.mysql.jdbc.Driver
"""

from __future__ import unicode_literals

import re

from django.conf import settings
from django.db import utils
from django.utils.encoding import force_text
from django.utils.functional import cached_property
from django.utils import six
from django.utils import timezone

from doj.db.backends import JDBCBaseDatabaseWrapper as BaseDatabaseWrapper
from doj.db.backends import JDBCBaseDatabaseFeatures as BaseDatabaseFeatures
from doj.db.backends import JDBCBaseDatabaseOperations as BaseDatabaseOperations
from doj.db.backends import JDBCCursorWrapper as CursorWrapper
from doj.db.backends import JDBCConnection

from doj.db.backends.mysql.client import DatabaseClient
from doj.db.backends.mysql.creation import DatabaseCreation
from doj.db.backends.mysql.introspection import DatabaseIntrospection
from doj.db.backends.mysql.validation import DatabaseValidation
from doj.db.backends.mysql.schema import DatabaseSchemaEditor

try:
    import pytz
except ImportError:
    pytz = None

DatabaseError = BaseDatabaseWrapper.DatabaseError
IntegrityError = BaseDatabaseWrapper.IntegrityError

# This should match the numerical portion of the version numbers (we can treat
# versions like 5.0.24 and 5.0.24a as the same). Based on the list of version
# at http://dev.mysql.com/doc/refman/4.1/en/news.html and
# http://dev.mysql.com/doc/refman/5.0/en/news.html .
server_version_re = re.compile(r'(\d{1,2})\.(\d{1,2})\.(\d{1,2})')


class DatabaseFeatures(BaseDatabaseFeatures):
    update_can_self_select = False
    allows_group_by_pk = True
    related_fields_match_type = True
    allow_sliced_subqueries = False
    has_bulk_insert = True
    has_select_for_update = True
    has_select_for_update_nowait = False
    supports_forward_references = False
    supports_long_model_names = False
    supports_binary_field = six.PY2
    supports_microsecond_precision = False
    supports_regex_backreferencing = False
    supports_date_lookup_using_string = False
    can_introspect_binary_field = False
    can_introspect_boolean_field = False
    supports_timezones = False
    requires_explicit_null_ordering_when_grouping = True
    allows_auto_pk_0 = False
    uses_savepoints = True
    atomic_transactions = False
    supports_column_check_constraints = False

    def __init__(self, connection):
        super(DatabaseFeatures, self).__init__(connection)

    @cached_property
    def _mysql_storage_engine(self):
        """
        Internal method used in Django tests. Don't rely on this from your code"
        :return: Table type
        """
        with self.connection.cursor() as cursor:
            cursor.execute('CREATE TABLE INTROSPECT_TEST (X INT)')
            # This command is MySQL specific; the second column
            # will tell you the default table type of the created
            # table. Since all Django's test tables will have the same
            # table type, that's enough to evaluate the feature.
            cursor.execute("SHOW TABLE STATUS WHERE Name='INTROSPECT_TEST'")
            result = cursor.fetchone()
            cursor.execute('DROP TABLE INTROSPECT_TEST')
        return result[1]

    @cached_property
    def can_introspect_foreign_keys(self):
        """
        Confirm support for introspected foreign keys
        """
        return self._mysql_storage_engine != 'MyISAM'

    @cached_property
    def has_zoneinfo_database(self):
        # MySQL accepts full time zones names (eg. Africa/Nairobi) but rejects
        # abbreviations (eg. EAT). When pytz isn't installed and the current
        # time zone is LocalTimezone (the only sensible value in this
        # context), the current time zone name will be an abbreviation. As a
        # consequence, MySQL cannot perform time zone conversions reliably.
        if pytz is None:
            return False

        # Test if the time zone definitions are installed.
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM mysql.time_zone LIMIT 1")
            return cursor.fetchone() is not None


class DatabaseOperations(BaseDatabaseOperations):
    compiler_module = "doj.db.backends.mysql.compiler"

    # MySQL stores positive fields as UNSIGNED ints.
    integer_field_ranges = dict(
        BaseDatabaseOperations.integer_field_ranges,
        PositiveSmallIntegerField=(0, 4294967295),
        PositiveIntegerField=(0, 18446744073709551615),
    )

    def date_extract_sql(self, lookup_type, field_name):
        # http://dev.mysql.com/doc/mysql/en/date-and-time-functions.html
        if lookup_type == 'week_day':
            # DAYOFWEEK() returns an integer, 1-7, Sunday=1.
            # Note: WEEKDAY() returns 0-6, Monday=0.
            return "DAYOFWEEK(%s)" % field_name
        else:
            return "EXTRACT(%s FROM %s)" % (lookup_type.upper(), field_name)

    def date_trunc_sql(self, lookup_type, field_name):
        fields = ['year', 'month', 'day', 'hour', 'minute', 'second']
        format = ('%%Y-', '%%m', '-%%d', ' %%H:', '%%i', ':%%s')  # Use double percents to escape.
        format_def = ('0000-', '01', '-01', ' 00:', '00', ':00')
        try:
            i = fields.index(lookup_type) + 1
        except ValueError:
            sql = field_name
        else:
            format_str = ''.join([f for f in format[:i]] + [f for f in format_def[i:]])
            sql = "CAST(DATE_FORMAT(%s, '%s') AS DATETIME)" % (field_name, format_str)
        return sql

    def datetime_extract_sql(self, lookup_type, field_name, tzname):
        if settings.USE_TZ:
            field_name = "CONVERT_TZ(%s, 'UTC', %%s)" % field_name
            params = [tzname]
        else:
            params = []
        # http://dev.mysql.com/doc/mysql/en/date-and-time-functions.html
        if lookup_type == 'week_day':
            # DAYOFWEEK() returns an integer, 1-7, Sunday=1.
            # Note: WEEKDAY() returns 0-6, Monday=0.
            sql = "DAYOFWEEK(%s)" % field_name
        else:
            sql = "EXTRACT(%s FROM %s)" % (lookup_type.upper(), field_name)
        return sql, params

    def datetime_trunc_sql(self, lookup_type, field_name, tzname):
        if settings.USE_TZ:
            field_name = "CONVERT_TZ(%s, 'UTC', %%s)" % field_name
            params = [tzname]
        else:
            params = []
        fields = ['year', 'month', 'day', 'hour', 'minute', 'second']
        format = ('%%Y-', '%%m', '-%%d', ' %%H:', '%%i', ':%%s')  # Use double percents to escape.
        format_def = ('0000-', '01', '-01', ' 00:', '00', ':00')
        try:
            i = fields.index(lookup_type) + 1
        except ValueError:
            sql = field_name
        else:
            format_str = ''.join([f for f in format[:i]] + [f for f in format_def[i:]])
            sql = "CAST(DATE_FORMAT(%s, '%s') AS DATETIME)" % (field_name, format_str)
        return sql, params

    def date_interval_sql(self, sql, connector, timedelta):
        return "(%s %s INTERVAL '%d 0:0:%d:%d' DAY_MICROSECOND)" % (sql, connector,
                timedelta.days, timedelta.seconds, timedelta.microseconds)

    def drop_foreignkey_sql(self):
        return "DROP FOREIGN KEY"

    def force_no_ordering(self):
        """
        "ORDER BY NULL" prevents MySQL from implicitly ordering by grouped
        columns. If no ordering would otherwise be applied, we don't want any
        implicit sorting going on.
        """
        return ["NULL"]

    def fulltext_search_sql(self, field_name):
        return 'MATCH (%s) AGAINST (%%s IN BOOLEAN MODE)' % field_name

    def last_executed_query(self, cursor, sql, params):
        # With MySQLdb, cursor objects have an (undocumented) "_last_executed"
        # attribute where the exact query sent to the database is saved.
        # See MySQLdb/cursors.py in the source distribution.
        return force_text(getattr(cursor, '_last_executed', None), errors='replace')

    def no_limit_value(self):
        # 2**64 - 1, as recommended by the MySQL documentation
        return 18446744073709551615

    def quote_name(self, name):
        if name.startswith("`") and name.endswith("`"):
            return name  # Quoting once is enough.
        return "`%s`" % name

    def random_function_sql(self):
        return 'RAND()'

    def last_insert_id(self, cursor, table_name, pk_name):
        cursor.execute("SELECT LAST_INSERT_ID()")
        return cursor.fetchone()[0]

    def sql_flush(self, style, tables, sequences, allow_cascade=False):
        # NB: The generated SQL below is specific to MySQL
        # 'TRUNCATE x;', 'TRUNCATE y;', 'TRUNCATE z;'... style SQL statements
        # to clear all tables of all data
        if tables:
            sql = ['SET FOREIGN_KEY_CHECKS = 0;']
            for table in tables:
                sql.append('%s %s;' % (
                    style.SQL_KEYWORD('TRUNCATE'),
                    style.SQL_FIELD(self.quote_name(table)),
                ))
            sql.append('SET FOREIGN_KEY_CHECKS = 1;')
            sql.extend(self.sequence_reset_by_name_sql(style, sequences))
            return sql
        else:
            return []

    def sequence_reset_by_name_sql(self, style, sequences):
        # Truncate already resets the AUTO_INCREMENT field from
        # MySQL version 5.0.13 onwards. Refs #16961.
        if self.connection.mysql_version < (5, 0, 13):
            return [
                "%s %s %s %s %s;" % (
                    style.SQL_KEYWORD('ALTER'),
                    style.SQL_KEYWORD('TABLE'),
                    style.SQL_TABLE(self.quote_name(sequence['table'])),
                    style.SQL_KEYWORD('AUTO_INCREMENT'),
                    style.SQL_FIELD('= 1'),
                ) for sequence in sequences
            ]
        else:
            return []

    def validate_autopk_value(self, value):
        # MySQLism: zero in AUTO_INCREMENT field does not work. Refs #17653.
        if value == 0:
            raise ValueError('The database backend does not accept 0 as a '
                             'value for AutoField.')
        return value

    def value_to_db_datetime(self, value):
        if value is None:
            return None

        # MySQL doesn't support tz-aware datetimes
        if timezone.is_aware(value):
            if settings.USE_TZ:
                value = value.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                raise ValueError("MySQL backend does not support timezone-aware datetimes when USE_TZ is False.")

        # MySQL doesn't support microseconds
        return six.text_type(value.replace(microsecond=0))

    def value_to_db_time(self, value):
        if value is None:
            return None

        # MySQL doesn't support tz-aware times
        if timezone.is_aware(value):
            raise ValueError("MySQL backend does not support timezone-aware times.")

        # MySQL doesn't support microseconds
        return six.text_type(value.replace(microsecond=0))

    def year_lookup_bounds_for_datetime_field(self, value):
        # Again, no microseconds
        first, second = super(DatabaseOperations, self).year_lookup_bounds_for_datetime_field(value)
        return [first.replace(microsecond=0), second.replace(microsecond=0)]

    def max_name_length(self):
        return 64

    def bulk_insert_sql(self, fields, num_values):
        items_sql = "(%s)" % ", ".join(["%s"] * len(fields))
        return "VALUES " + ", ".join([items_sql] * num_values)

    def combine_expression(self, connector, sub_expressions):
        """
        MySQL requires special cases for ^ operators in query expressions
        """
        if connector == '^':
            return 'POW(%s)' % ','.join(sub_expressions)
        return super(DatabaseOperations, self).combine_expression(connector, sub_expressions)


class DatabaseWrapper(BaseDatabaseWrapper):
    vendor = 'mysql'
    jdbc_driver_class_name = 'com.mysql.jdbc.Driver'
    jdbc_connection_url_pattern = 'jdbc:mysql://%(HOST)s:%(PORT)s/%(NAME)s?zeroDateTimeBehavior=convertToNull'
    jdbc_default_host = 'localhost'
    jdbc_default_port = 3306
    jdbc_default_name = 'mysql'
    operators = {
        'exact': '= %s',
        'iexact': 'LIKE %s',
        'contains': 'LIKE BINARY %s',
        'icontains': 'LIKE %s',
        'regex': 'REGEXP BINARY %s',
        'iregex': 'REGEXP %s',
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': 'LIKE BINARY %s',
        'endswith': 'LIKE BINARY %s',
        'istartswith': 'LIKE %s',
        'iendswith': 'LIKE %s',
    }

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = DatabaseValidation(self)

    def init_connection_state(self):
        with self.cursor() as cursor:
            # SQL_AUTO_IS_NULL in MySQL controls whether an AUTO_INCREMENT column
            # on a recently-inserted row will return when the field is tested for
            # NULL.  Disabling this value brings this aspect of MySQL in line with
            # SQL standards.
            cursor.execute('SET SQL_AUTO_IS_NULL = 0')

    def _rollback(self):
        try:
            BaseDatabaseWrapper._rollback(self)
        except self.NotSupportedError:
            pass

    def disable_constraint_checking(self):
        """
        Disables foreign key checks, primarily for use in adding rows with forward references. Always returns True,
        to indicate constraint checks need to be re-enabled.
        """
        self.cursor().execute('SET foreign_key_checks=0')
        return True

    def enable_constraint_checking(self):
        """
        Re-enable foreign key checks after they have been disabled.
        """
        # Override needs_rollback in case constraint_checks_disabled is
        # nested inside transaction.atomic.
        self.needs_rollback, needs_rollback = False, self.needs_rollback
        try:
            self.cursor().execute('SET foreign_key_checks=1')
        finally:
            self.needs_rollback = needs_rollback

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
                        % (table_name, bad_row[0],
                        table_name, column_name, bad_row[1],
                        referenced_table_name, referenced_column_name))

    def schema_editor(self, *args, **kwargs):
        "Returns a new instance of this backend's SchemaEditor"
        return DatabaseSchemaEditor(self, *args, **kwargs)

    def is_usable(self):
        try:
            self.connection.cursor().execute("SELECT 1")
        except self.Error:
            return False
        else:
            return True

    @cached_property
    def mysql_version(self):
        with self.temporary_connection():
            server_info = self.connection.get_server_info()
        match = server_version_re.match(server_info)
        if not match:
            raise Exception('Unable to determine MySQL version from version string %r' % server_info)
        return tuple(int(x) for x in match.groups())

    @staticmethod
    def _set_default_isolation_level(connection):
        """
        Make transactions transparent to all cursors. Must be called by zxJDBC backends
        after instantiating a connection.

        :param connection: zxJDBC connection
        """
        jdbc_connection = connection.__connection__
        jdbc_connection.setTransactionIsolation(JDBCConnection.TRANSACTION_REPEATABLE_READ)