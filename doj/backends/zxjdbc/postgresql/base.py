"""
PostgreSQL database backend for Django/Jython
"""
try:
    from com.ziclix.python.sql import zxJDBC as Database
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading zxJDBC module: %s" % e)

from django.db.backends import BaseDatabaseFeatures, BaseDatabaseValidation
from django.db.backends.postgresql.operations import DatabaseOperations as PostgresqlDatabaseOperations
from django.db.backends.postgresql.client import DatabaseClient
from django.db.backends.postgresql.introspection import DatabaseIntrospection
from doj.backends.zxjdbc.postgresql.creation import DatabaseCreation

from doj.backends.zxjdbc.common import (
    zxJDBCDatabaseWrapper, zxJDBCOperationsMixin, zxJDBCFeaturesMixin, 
    zxJDBCCursorWrapper, set_default_isolation_level)

from com.ziclix.python.sql.handler import PostgresqlDataHandler
from UserDict import DictMixin

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError

class DatabaseFeatures(zxJDBCFeaturesMixin, BaseDatabaseFeatures):
    pass


class DatabaseOperations(zxJDBCOperationsMixin, PostgresqlDatabaseOperations):
    pass # The mixin contains all what is needed

class SettingsModuleAsDict(DictMixin):
    def __init__(self, module):
        self.module = module
    def __getitem__(self, name):
        return getattr(self.module, name)
    def __setitem__(self, name, value):
        setattr(self.module, name, value)
    def __delitem__(self, name):
        self.module.__delattr__(name)
    def keys(self):
        return dir(self.module)

class DatabaseWrapper(zxJDBCDatabaseWrapper):
    driver_class_name = "org.postgresql.Driver"
    jdbc_url_pattern = \
        "jdbc:postgresql://%(HOST)s%(PORT)s/%(NAME)s"
    operators = {
        'exact': '= %s',
        'iexact': 'ILIKE %s',
        'contains': 'LIKE %s',
        'icontains': 'ILIKE %s',
        'regex': '~ %s',
        'iregex': '~* %s',
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': 'LIKE %s',
        'endswith': 'LIKE %s',
        'istartswith': 'ILIKE %s',
        'iendswith': 'ILIKE %s',
    }

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation(self)

    def _cursor(self):
        if self.connection is None:
            self.connection = self.new_connection()
            # make transactions transparent to all cursors
            set_default_isolation_level(self.connection)
        real_cursor = self.connection.cursor()
        # Use the PostgreSQL DataHandler for better compatibility:
        real_cursor.datahandler = PostgresqlDataHandler(real_cursor.datahandler)
        return CursorWrapper(real_cursor)


class CursorWrapper(zxJDBCCursorWrapper):
    def execute(self, *args, **kwargs):
        try:
            super(CursorWrapper, self).execute(*args, **kwargs)
        except Database.Error:
            # PostgreSQL connections become unusable after an exception
            # occurs, unless the current transaction is rollback'ed.
            self.connection.rollback()
            raise
    def executemany(self, *args, **kwargs):
        try:
            super(CursorWrapper, self).executemany(*args, **kwargs)
        except Database.Error:
            # PostgreSQL connections become unusable after an exception
            # occurs, unless the current transaction is rollback'ed.
            self.connection.rollback()
            raise


import platform
if tuple(platform.python_version_tuple()) < ('2', '5', '2'):
    # Workaround Jython bug http://bugs.jython.org/issue1499: PostgreSQL
    # datahandler should return Decimals instead of floats for NUMERIC/DECIMAL
    # columns
    OriginalPostgresqlDataHandler = PostgresqlDataHandler
    from java.sql import Types
    from decimal import Decimal
    class PostgresqlDataHandler(OriginalPostgresqlDataHandler):
        def getPyObject(self, set, col, type):
            if type in (Types.NUMERIC, Types.DECIMAL):
                value = set.getBigDecimal(col)
                if value is None:
                    return None
                else:
                    return Decimal(str(value))
            else:
                return OriginalPostgresqlDataHandler.getPyObject(
                    self, set, col, type)
