# -*- coding: utf-8 -*-

from java.sql import Connection
from com.ziclix.python.sql import zxJDBC

from datetime import datetime

from django.db.backends import BaseDatabaseWrapper, BaseDatabaseFeatures, BaseDatabaseOperations, \
    BaseDatabaseIntrospection, BaseDatabaseClient, BaseDatabaseValidation, FieldInfo
from django.db.backends.creation import BaseDatabaseCreation
from django.db.backends.schema import BaseDatabaseSchemaEditor

__all__ = (
    'JDBCBaseDatabaseWrapper',
    'JDBCBaseDatabaseFeatures',
    'JDBCBaseDatabaseOperations',
    'JDBCBaseDatabaseIntrospection',
    'JDBCBaseDatabaseClient',
    'JDBCBaseDatabaseValidation',
    'JDBCBaseDatabaseCreation',
    'JDBCFieldInfo',
    'JDBCBaseDatabaseSchemaEditor',
    'JDBCCursorWrapper',
    'JDBCConnection',
)


class JDBCBaseDatabaseWrapper(BaseDatabaseWrapper):
    """
    Represents a database connection using zxJDBC.
    """
    jdbc_default_host = None
    jdbc_default_port = None
    jdbc_default_name = None
    jdbc_driver_class_name = None
    jdbc_connection_url_pattern = None

    Database = zxJDBC
    Error = Database.Error
    NotSupportedError = Database.NotSupportedError
    DatabaseError = Database.DatabaseError
    IntegrityError = Database.IntegrityError
    ProgrammingError = Database.ProgrammingError

    def __init__(self, *args, **kwargs):
        super(JDBCBaseDatabaseWrapper, self).__init__(*args, **kwargs)

    def get_jdbc_settings(self):
        settings_dict = dict(self.settings_dict)  # copy instead of reference

        if not settings_dict.get('HOST', None):
            settings_dict['HOST'] = self.jdbc_default_host
        if not settings_dict.get('PORT', None):
            settings_dict['PORT'] = self.jdbc_default_port
        if not settings_dict.get('NAME', None):
            settings_dict['NAME'] = self.jdbc_default_name

        return settings_dict

    def get_jdbc_driver_class_name(self):
        return self.jdbc_driver_class_name

    def get_jdbc_connection_url(self):
        return self.jdbc_connection_url_pattern % self.get_jdbc_settings()

    def get_new_jndi_connection(self):
        """
        Returns a zxJDBC Connection object obtained from a JNDI data source if
        the settings dictionary contains the JNDI_NAME entry on the
        DATABASE_OPTIONS dictionary, or None if it doesn't.
        :return: zxJDBC Connection
        """
        settings_dict = dict(self.settings_dict)

        if 'OPTIONS' not in settings_dict:
            return None
        if 'JNDI_NAME' not in settings_dict['OPTIONS']:
            return None

        name = settings_dict['OPTIONS']['JNDI_NAME']
        props = settings_dict['OPTIONS'].get('JNDI_CONTEXT_OPTIONS', {})

        return zxJDBC.lookup(name, keywords=props)

    def get_connection_params(self):
        settings_dict = dict(self.settings_dict)

        # None may be used to connect to the default 'postgres' db
        if settings_dict['NAME'] == '':
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured(
                "settings.DATABASES is improperly configured. "
                "Please supply the NAME value.")

        settings_dict['NAME'] = settings_dict['NAME'] or self.jdbc_default_name
        return settings_dict

    def get_new_connection(self, conn_params):
        connection = self.get_new_jndi_connection()

        if not connection:
            connection = zxJDBC.connect(self.get_jdbc_connection_url(),
                                        conn_params['USER'],
                                        conn_params['PASSWORD'],
                                        self.jdbc_driver_class_name,
                                        **conn_params['OPTIONS'])
            self._set_default_isolation_level(connection)
        return connection

    def create_cursor(self):
        return JDBCCursorWrapper(self.connection.cursor())

    def _set_autocommit(self, autocommit):
        self.connection.autocommit = autocommit

    @staticmethod
    def _set_default_isolation_level(connection):
        """
        Make transactions transparent to all cursors. Must be called by zxJDBC backends
        after instantiating a connection.

        :param connection: zxJDBC connection
        """
        jdbc_connection = connection.__connection__
        jdbc_connection.setTransactionIsolation(JDBCConnection.TRANSACTION_READ_COMMITTED)


class JDBCBaseDatabaseOperations(BaseDatabaseOperations):
    """
    zxJDBC supports dates, times, datetimes and decimal directly, so we
    override the convert methods of django here.
    """
    def value_to_db_date(self, value):
        return value

    def value_to_db_datetime(self, value):
        return value

    def value_to_db_time(self, value):
        return value

    def value_to_db_decimal(self, value, max_digits, decimal_places):
        return value

    def year_lookup_bounds(self, value):
        first = datetime(value, 1, 1)
        second = datetime(value, 12, 31, 23, 59, 59, 999999)
        return [first, second]


class JDBCCursorWrapper(object):
    """
    A simple wrapper to do the "%s" -> "?" replacement before running zxJDBC's
    execute or executemany.
    """
    def __init__(self, cursor):
        self.cursor = cursor

    def __get_arraysize(self):
        return self.cursor.arraysize

    def __set_arraysize(self, size):
        self.cursor.arraysize = size

    def __get_rowcount(self):
        if self.cursor.updatecount > self.cursor.rowcount:
            return self.cursor.updatecount
        return self.cursor.rowcount

    def __getattr__(self, attr):
        return getattr(self.cursor, attr)

    def __iter__(self):
        return iter(self.next, None)

    def execute(self, sql, params=None):
        if not params:
            params = tuple()
        sql = sql % (('?',) * len(params))
        self.cursor.execute(sql, params)

    def executemany(self, sql, param_list):
        if len(param_list) > 0:
            sql = sql % (('?',) * len(param_list[0]))
        self.cursor.executemany(sql, param_list)

    def callproc(self, procname, parameters=None):
        return self.cursor.callproc(procname, parameters)

    def close(self):
        return self.cursor.close()

    def fetchone(self):
        try:
            return self.cursor.fetchone()
        except JDBCBaseDatabaseWrapper.DatabaseError:
            return None

    def fetchmany(self, size=None):
        if not size:
            size = self.cursor.arraysize

        # `fetchmany` may rise an IndexError if the result set is
        # smaller than the size parameter. We fallback to `fetchall`
        # in that case.
        try:
            return self.cursor.fetchmany(size)
        except (IndexError, JDBCBaseDatabaseWrapper.DatabaseError):
            return self.cursor.fetchall()

    def fetchall(self):
        try:
            return self.cursor.fetchall()
        except (IndexError, JDBCBaseDatabaseWrapper.DatabaseError):
            return []

    def nextset(self):
        return self.cursor.nextset()

    def setinputsizes(self, sizes):
        return self.cursor.setinputsizes(sizes)

    def setoutputsize(self, sizes, column=None):
        return self.cursor.setoutputsize(sizes, column)

    arraysize = property(fget=__get_arraysize, fset=__set_arraysize)
    rowcount = property(fget=__get_rowcount)


class JDBCBaseDatabaseFeatures(BaseDatabaseFeatures):
    needs_datetime_string_cast = False


class JDBCBaseDatabaseIntrospection(BaseDatabaseIntrospection):
    data_types_reverse = {
        zxJDBC.BIGINT: 'BigIntegerField',
        zxJDBC.BINARY: 'BinaryField',
        zxJDBC.BIT: 'BooleanField',
        zxJDBC.BLOB: 'BinaryField',
        zxJDBC.BOOLEAN: 'BooleanField',
        zxJDBC.CHAR: 'CharField',
        zxJDBC.CLOB: 'TextField',
        zxJDBC.DATE: 'DateField',
        zxJDBC.DATETIME: 'DateTimeField',
        zxJDBC.DECIMAL: 'DecimalField',
        zxJDBC.DOUBLE: 'FloatField',
        zxJDBC.FLOAT: 'FloatField',
        zxJDBC.INTEGER: 'IntegerField',
        zxJDBC.LONGNVARCHAR: 'TextField',
        zxJDBC.LONGVARBINARY: 'BinaryField',
        zxJDBC.LONGVARCHAR: 'TextField',
        zxJDBC.NCHAR: 'CharField',
        zxJDBC.NCLOB: 'TextField',
        zxJDBC.NUMBER: 'IntegerField',
        zxJDBC.NVARCHAR: 'CharField',
        zxJDBC.REAL: 'FloatField',
        zxJDBC.SMALLINT: 'SmallIntegerField',
        zxJDBC.STRING: 'TextField',
        zxJDBC.TIME: 'TimeField',
        zxJDBC.TIMESTAMP: 'DateTimeField',
        zxJDBC.TINYINT: 'SmallIntegerField',
        zxJDBC.VARBINARY: 'BinaryField',
        zxJDBC.VARCHAR: 'CharField',
    }


class JDBCBaseDatabaseClient(BaseDatabaseClient):
    pass


class JDBCBaseDatabaseValidation(BaseDatabaseValidation):
    pass


class JDBCBaseDatabaseCreation(BaseDatabaseCreation):
    pass


class JDBCFieldInfo(FieldInfo):
    pass


class JDBCBaseDatabaseSchemaEditor(BaseDatabaseSchemaEditor):
    pass


class JDBCConnection(Connection):
    pass