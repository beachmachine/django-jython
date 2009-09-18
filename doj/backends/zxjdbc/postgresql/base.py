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
from UserDict import DictMixin
import django

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
        if django.VERSION < (1, 1):
            # Compatibility with 1.0 ORM API
            self.client = DatabaseClient()
        else:
            self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation()

    def _cursor(self, *args):
        if django.VERSION < (1, 1):
            # Compatibility with 1.0 ORM API
            settings, = args
            settings_dict = SettingsModuleAsDict(settings)
            settings_dict['DATABASE_OPTIONS'] = self.options
        else:
            settings_dict = self.settings_dict
        return self._cursor_from_settings_dict(settings_dict)

    def _cursor_from_settings_dict(self, settings_dict):
        if self.connection is None:
            if settings_dict['DATABASE_NAME'] == '':
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured("You need to specify DATABASE_NAME in your Django settings file.")
            host = settings_dict['DATABASE_HOST'] or 'localhost'
            port = (settings_dict['DATABASE_PORT'] 
                    and (':%s' % settings_dict['DATABASE_PORT'])
                    or '')
            conn_string = "jdbc:postgresql://%s%s/%s" % (
                    host, port, settings_dict['DATABASE_NAME'])
            self.connection = Database.connect(
                    conn_string,
                    settings_dict['DATABASE_USER'],
                    settings_dict['DATABASE_PASSWORD'],
                    'org.postgresql.Driver',
                    **settings_dict['DATABASE_OPTIONS'])
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
