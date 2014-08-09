# -*- coding: utf-8 -*-
"""
PostgreSQL database backend for DOJ.

Requires JDBC driver: org.postgresql.Driver
"""

from django.conf import settings
from django.db.utils import InterfaceError
from django.utils.functional import cached_property
from django.utils.timezone import utc

from doj.db.backends import JDBCBaseDatabaseWrapper as BaseDatabaseWrapper
from doj.db.backends import JDBCBaseDatabaseFeatures as BaseDatabaseFeatures
from doj.db.backends import JDBCBaseDatabaseValidation as BaseDatabaseValidation
from doj.db.backends import JDBCCursorWrapper as CursorWrapper

from doj.db.backends.postgresql.operations import DatabaseOperations
from doj.db.backends.postgresql.client import DatabaseClient
from doj.db.backends.postgresql.creation import DatabaseCreation
from doj.db.backends.postgresql.version import get_version
from doj.db.backends.postgresql.introspection import DatabaseIntrospection
from doj.db.backends.postgresql.schema import DatabaseSchemaEditor

DatabaseError = BaseDatabaseWrapper.DatabaseError
IntegrityError = BaseDatabaseWrapper.IntegrityError


def utc_tzinfo_factory(offset):
    if offset != 0:
        raise AssertionError("database connection isn't set to UTC")
    return utc


class DatabaseFeatures(BaseDatabaseFeatures):
    needs_datetime_string_cast = False
    can_return_id_from_insert = True
    requires_rollback_on_dirty_transaction = True
    has_real_datatype = True
    can_defer_constraint_checks = True
    has_select_for_update = True
    has_select_for_update_nowait = True
    has_bulk_insert = True
    uses_savepoints = True
    supports_tablespaces = True
    supports_transactions = True
    can_introspect_ip_address_field = True
    can_introspect_small_integer_field = True
    can_distinct_on_fields = True
    can_rollback_ddl = True
    supports_combined_alters = True
    nulls_order_largest = True
    closed_cursor_error_class = InterfaceError
    has_case_insensitive_like = False
    requires_sqlparse_for_splitting = False


class DatabaseWrapper(BaseDatabaseWrapper):
    vendor = 'postgresql'
    jdbc_driver_class_name = 'org.postgresql.Driver'
    jdbc_connection_url_pattern = 'jdbc:postgresql://%(HOST)s:%(PORT)s/%(NAME)s?stringtype=unspecified'
    jdbc_default_host = 'localhost'
    jdbc_default_port = 5432
    jdbc_default_name = 'postgres'
    operators = {
        'exact': '= %s',
        'iexact': '= UPPER(%s)',
        'contains': 'LIKE %s',
        'icontains': 'LIKE UPPER(%s)',
        'regex': '~ %s',
        'iregex': '~* %s',
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': 'LIKE %s',
        'endswith': 'LIKE %s',
        'istartswith': 'LIKE UPPER(%s)',
        'iendswith': 'LIKE UPPER(%s)',
    }

    pattern_ops = {
        'startswith': "LIKE %s || '%%%%'",
        'istartswith': "LIKE UPPER(%s) || '%%%%'",
    }

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation(self)

    def init_connection_state(self):
        settings_dict = dict(self.settings_dict)
        tz = 'UTC' if settings.USE_TZ else settings_dict.get('TIME_ZONE')

        if tz:
            try:
                get_parameter_status = self.connection.get_parameter_status
            except AttributeError:
                conn_tz = None
            else:
                conn_tz = get_parameter_status('TimeZone')

            if conn_tz != tz:
                cursor = CursorWrapper(self.connection.cursor())
                try:
                    cursor.execute(self.ops.set_time_zone_sql() % self.ops.quote_name(tz))
                finally:
                    cursor.close()

                # Commit after setting the time zone (see #17062)
                if not self.get_autocommit():
                    self.connection.commit()

    def check_constraints(self, table_names=None):
        """
        To check constraints, we set constraints to immediate. Then, when, we're done we must ensure they
        are returned to deferred.
        """
        self.cursor().execute('SET CONSTRAINTS ALL IMMEDIATE')
        self.cursor().execute('SET CONSTRAINTS ALL DEFERRED')

    def is_usable(self):
        try:
            self.connection.cursor().execute("SELECT 1")
        except self.Error:
            return False
        else:
            return True

    def schema_editor(self, *args, **kwargs):
        """
        Returns a new instance of this backend's SchemaEditor.

        :param args: Arguments for DatabaseSchemaEditor
        :param kwargs: Keyword arguments for DatabaseSchemaEditor
        :return: DatabaseSchemaEditor instance
        """
        return DatabaseSchemaEditor(self, *args, **kwargs)

    @cached_property
    def pg_version(self):
        with self.temporary_connection():
            return get_version(self.connection)
