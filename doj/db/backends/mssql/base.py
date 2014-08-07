# -*- coding: utf-8 -*-
"""
Microsoft SQL Server database backend for DOJ.

Requires JDBC driver: net.sourceforge.jtds.jdbc.Driver
"""

from __future__ import absolute_import, unicode_literals

from django.db.utils import IntegrityError as DjangoIntegrityError, InterfaceError as DjangoInterfaceError
from django.utils.functional import cached_property

from doj.db.backends import JDBCBaseDatabaseWrapper as BaseDatabaseWrapper
from doj.db.backends import JDBCBaseDatabaseFeatures as BaseDatabaseFeatures
from doj.db.backends import JDBCBaseDatabaseClient as BaseDatabaseClient
from doj.db.backends import JDBCBaseDatabaseValidation as BaseDatabaseValidation
from doj.db.backends import JDBCCursorWrapper as CursorWrapper

from doj.db.backends.mssql.introspection import DatabaseIntrospection
from doj.db.backends.mssql.creation import DatabaseCreation
from doj.db.backends.mssql.operations import DatabaseOperations
from doj.db.backends.mssql.schema import DatabaseSchemaEditor

try:
    import pytz
except ImportError:
    pytz = None

VERSION_SQL2000 = 8
VERSION_SQL2005 = 9
VERSION_SQL2008 = 10
VERSION_SQL2012 = 11

IntegrityError = BaseDatabaseWrapper.IntegrityError


class DatabaseFeatures(BaseDatabaseFeatures):
    uses_custom_query_class = True
    has_bulk_insert = False

    # DateTimeField doesn't support timezones, only DateTimeOffsetField
    supports_timezones = False
    supports_sequence_reset = False

    can_return_id_from_insert = True

    supports_regex_backreferencing = False

    supports_tablespaces = True

    supports_nullable_unique_constraints = False
    supports_partially_nullable_unique_constraints = False

    can_introspect_autofield = True
    can_introspect_small_integer_field = True

    supports_subqueries_in_group_by = False

    allow_sliced_subqueries = False

    uses_savepoints = True

    supports_paramstyle_pyformat = False

    closed_cursor_error_class = DjangoInterfaceError

    # connection_persists_old_columns = True

    requires_literal_defaults = True

    @cached_property
    def has_zoneinfo_database(self):
        return pytz is not None

    # Dict of test import path and list of versions on which it fails
    failing_tests = {
        # Some tests are known to fail with DOJ/mssql.
        'aggregation.tests.BaseAggregateTestCase.test_dates_with_aggregation': [(1, 6), (1, 7)],
        'aggregation_regress.tests.AggregationTests.test_more_more_more': [(1, 6), (1, 7)],

        # MSSQL throws an arithmetic overflow error.
        'expressions_regress.tests.ExpressionOperatorTests.test_righthand_power': [(1, 7)],

        # The migrations and schema tests also fail massively at this time.
        'migrations.test_operations.OperationTests.test_alter_field_pk': [(1, 7)],

    }


class DatabaseWrapper(BaseDatabaseWrapper):
    vendor = 'microsoft'
    jdbc_driver_class_name = 'net.sourceforge.jtds.jdbc.Driver'
    jdbc_connection_url_pattern = 'jdbc:jtds:sqlserver://%(HOST)s:%(PORT)s/%(NAME)s'
    jdbc_default_host = 'localhost'
    jdbc_default_port = 1433
    jdbc_default_name = 'master'
    operators = {
        "exact": "= %s",
        "iexact": "LIKE %s ESCAPE '\\'",
        "contains": "LIKE %s ESCAPE '\\'",
        "icontains": "LIKE %s ESCAPE '\\'",
        "gt": "> %s",
        "gte": ">= %s",
        "lt": "< %s",
        "lte": "<= %s",
        "startswith": "LIKE %s ESCAPE '\\'",
        "endswith": "LIKE %s ESCAPE '\\'",
        "istartswith": "LIKE %s ESCAPE '\\'",
        "iendswith": "LIKE %s ESCAPE '\\'",
    }

    def __init__(self, *args, **kwargs):
        self.use_transactions = kwargs.pop('use_transactions', None)

        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        try:
            self.command_timeout = int(self.settings_dict.get('COMMAND_TIMEOUT', 30))
        except ValueError:
            self.command_timeout = 30

        options = self.settings_dict.get('OPTIONS', {})
        try:
            self.cast_avg_to_float = not bool(options.get('disable_avg_cast', False))
        except ValueError:
            self.cast_avg_to_float = False

        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = BaseDatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation(self)

    def init_connection_state(self):
        pass

    def disable_constraint_checking(self):
        """
        Turn off constraint checking for every table
        """
        cursor = self.cursor()
        cursor.execute('EXEC sp_MSforeachtable "ALTER TABLE ? NOCHECK CONSTRAINT all"')
        return True

    def enable_constraint_checking(self):
        """
        Turn on constraint checking for every table
        """
        cursor = self.cursor()
        cursor.execute('EXEC sp_MSforeachtable "ALTER TABLE ? WITH NOCHECK CHECK CONSTRAINT all"')

    def check_constraints(self, table_names=None):
        """
        Check the table constraints.
        """
        cursor = self.cursor()

        if not table_names:
            cursor.execute('DBCC CHECKCONSTRAINTS WITH ALL_CONSTRAINTS')
            if cursor.description:
                raise DjangoIntegrityError(cursor.fetchall())
        else:
            qn = self.ops.quote_name
            for name in table_names:
                cursor.execute('DBCC CHECKCONSTRAINTS({0}) WITH ALL_CONSTRAINTS'.format(
                    qn(name)
                ))
                if cursor.description:
                    raise DjangoIntegrityError(cursor.fetchall())

    # MS SQL Server doesn't support explicit savepoint commits; savepoints are
    # implicitly committed with the transaction.
    # Ignore them.
    def _savepoint_commit(self, sid):
        queries_log = self.queries

        if queries_log:
            queries_log.append({
                'sql': '-- RELEASE SAVEPOINT %s -- (because assertNumQueries)' % self.ops.quote_name(sid),
                'time': '0.000',
            })

    def is_usable(self):
        try:
            self.connection.cursor().execute("SELECT 1")
        except self.Error:
            return False
        else:
            return True

    def schema_editor(self, *args, **kwargs):
        return DatabaseSchemaEditor(self, *args, **kwargs)
