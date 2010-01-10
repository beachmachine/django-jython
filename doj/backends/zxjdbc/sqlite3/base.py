"""
SQLite3 backend for Django/Jython.
"""

from django.db.backends import BaseDatabaseFeatures
from django.db.backends import BaseDatabaseOperations, BaseDatabaseValidation, util
from django.db.backends.sqlite3.client import DatabaseClient
from django.db.backends.sqlite3.creation import DatabaseCreation
from django.db.backends.sqlite3.introspection import DatabaseIntrospection


try:
    from com.ziclix.python.sql import zxJDBC as Database
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading zxJDBC module: %s" % e)

try:
    from org.sqlite import JDBC
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading SQLite3 JDBC driver: %s" % e)


from doj.backends.zxjdbc.common import (
    zxJDBCDatabaseWrapper, zxJDBCOperationsMixin, zxJDBCFeaturesMixin, 
    zxJDBCCursorWrapper)
from org.sqlite import Function

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError

# Copied from sqlite3 backend
class DatabaseFeatures(zxJDBCFeaturesMixin, BaseDatabaseFeatures):
    # SQLite cannot handle us only partially reading from a cursor's result set
    # and then writing the same rows to the database in another cursor. This
    # setting ensures we always read result sets fully into memory all in one
    # go.
    can_use_chunked_reads = False

# Copied from sqlite3 backend
class DatabaseOperations(zxJDBCOperationsMixin, BaseDatabaseOperations):
    def date_extract_sql(self, lookup_type, field_name):
        # sqlite doesn't support extract, so we fake it with the user-defined
        # function django_extract that's registered in connect().
        return 'django_extract("%s", %s)' % (lookup_type.lower(), field_name)

    def date_trunc_sql(self, lookup_type, field_name):
        # sqlite doesn't support DATE_TRUNC, so we fake it with a user-defined
        # function django_date_trunc that's registered in connect().
        return 'django_date_trunc("%s", %s)' % (lookup_type.lower(), field_name)

    def drop_foreignkey_sql(self):
        return ""

    def pk_default_value(self):
        return 'NULL'

    def quote_name(self, name):
        if name.startswith('"') and name.endswith('"'):
            return name # Quoting once is enough.
        return '"%s"' % name

    def no_limit_value(self):
        return -1

    def sql_flush(self, style, tables, sequences):
        # NB: The generated SQL below is specific to SQLite
        # Note: The DELETE FROM... SQL generated below works for SQLite databases
        # because constraints don't exist
        sql = ['%s %s %s;' % \
                (style.SQL_KEYWORD('DELETE'),
                 style.SQL_KEYWORD('FROM'),
                 style.SQL_FIELD(self.quote_name(table))
                 ) for table in tables]
        # Note: No requirement for reset of auto-incremented indices (cf. other
        # sql_flush() implementations). Just return SQL at this point
        return sql

# With the exception of _cursor and zxJDBCDatabaseWrapper properties, also
# copied from the sqlite3 backend:
class DatabaseWrapper(zxJDBCDatabaseWrapper):
    driver_class_name = 'org.sqlite.JDBC'
    jdbc_url_pattern = "jdbc:sqlite:%(DATABASE_NAME)s"
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

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        self.features = DatabaseFeatures()
        self.ops = DatabaseOperations()
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation()

    def _cursor(self):
        if self.connection is None:
            self.connection = self.new_connection()
            # set_default_isolation_level(self.connection) not working :(
            # Register extract, date_trunc, and regexp functions.
            _create_function(self.connection.__connection__,
                             "django_extract", 2, _sqlite_extract)
            _create_function(self.connection.__connection__,
                             "django_date_trunc", 2, _sqlite_date_trunc)
            _create_function(self.connection.__connection__,
                             "regexp", 2, _sqlite_regexp)
        return CursorWrapper(self.connection.cursor())

    def close(self):
        from django.conf import settings
        # If database is in memory, closing the connection destroys the
        # database. To prevent accidental data loss, ignore close requests on
        # an in-memory db.
        if self.settings_dict['DATABASE_NAME'] != ":memory:":
            BaseDatabaseWrapper.close(self)

CursorWrapper = zxJDBCCursorWrapper

def _create_function(conn, name, num_args, py_func):
    class func(Function):
        def xFunc(self):
            assert self.args() == num_args
            args = [self.value_string(n) for n in xrange(0, num_args)]
            ret = py_func(*args)
            self.result(ret)
    Function.create(conn, name, func())

# Functions copied from sqlite3 backend:

def _sqlite_extract(lookup_type, dt):
    try:
        dt = util.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    return getattr(dt, lookup_type)

def _sqlite_date_trunc(lookup_type, dt):
    try:
        dt = util.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    if lookup_type == 'year':
        return "%i-01-01 00:00:00" % dt.year
    elif lookup_type == 'month':
        return "%i-%02i-01 00:00:00" % (dt.year, dt.month)
    elif lookup_type == 'day':
        return "%i-%02i-%02i 00:00:00" % (dt.year, dt.month, dt.day)

def _sqlite_regexp(re_pattern, re_string):
    import re
    try:
        return bool(re.search(re_pattern, re_string))
    except:
        return False
