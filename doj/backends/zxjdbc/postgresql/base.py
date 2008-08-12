"""
PostgreSQL database backend for Django/Jython
"""
try:
    from com.ziclix.python.sql import zxJDBC as Database
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading zxJDBC module: %s" % e)

from django.db.backends import BaseDatabaseWrapper, BaseDatabaseFeatures, BaseDatabaseValidation
from django.db.backends.postgresql.operations import DatabaseOperations as PostgresqlDatabaseOperations
from django.db.backends.postgresql.client import DatabaseClient
from django.db.backends.postgresql.introspection import DatabaseIntrospection
from doj.backends.zxjdbc.postgresql.creation import DatabaseCreation

from doj.backends.zxjdbc.common import zxJDBCOperationsMixin, zxJDBCFeaturesMixin
from doj.backends.zxjdbc.common import zxJDBCCursorWrapper, set_default_isolation_level
from com.ziclix.python.sql.handler import PostgresqlDataHandler

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError

class DatabaseFeatures(zxJDBCFeaturesMixin, BaseDatabaseFeatures):
    pass


class DatabaseOperations(zxJDBCOperationsMixin, PostgresqlDatabaseOperations):
    pass # The mixin contains all what is needed


class DatabaseWrapper(BaseDatabaseWrapper):
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

        self.features = DatabaseFeatures()
        self.ops = DatabaseOperations()
        self.client = DatabaseClient()
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation()

    def _cursor(self, settings):
        if self.connection is None:
            if settings.DATABASE_NAME == '':
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured("You need to specify DATABASE_NAME in your Django settings file.")
            host = settings.DATABASE_HOST or 'localhost'
            port = settings.DATABASE_PORT and (':%s' % settings.DATABASE_PORT) or ''
            conn_string = "jdbc:postgresql://%s%s/%s" % (host, port,
                                                         settings.DATABASE_NAME)
            self.connection = Database.connect(conn_string,
                                               settings.DATABASE_USER,
                                               settings.DATABASE_PASSWORD,
                                               'org.postgresql.Driver',
                                               **self.options)
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
