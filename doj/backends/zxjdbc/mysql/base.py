"""
MySQL database backend for Django/Jython
"""
try:
    from com.ziclix.python.sql import zxJDBC as Database
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading zxJDBC module: %s" % e)

from django.db.backends import BaseDatabaseWrapper, BaseDatabaseFeatures, BaseDatabaseValidation
from django.db.backends import BaseDatabaseOperations
#from django.db.backends.mysql.base import DatabaseOperations as MysqlDatabaseOperations
from django.db.backends.mysql.client import DatabaseClient
#from django.db.backends.mysql.introspection import DatabaseIntrospection
from doj.backends.zxjdbc.mysql.creation import DatabaseCreation

from doj.backends.zxjdbc.mysql.introspection import DatabaseIntrospection
from doj.backends.zxjdbc.common import zxJDBCOperationsMixin, zxJDBCFeaturesMixin
from doj.backends.zxjdbc.common import zxJDBCCursorWrapper, set_default_isolation_level
from doj.backends.zxjdbc.common import zxJDBCDatabaseWrapper
from com.ziclix.python.sql.handler import MySQLDataHandler

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError

class DatabaseFeatures(zxJDBCFeaturesMixin, BaseDatabaseFeatures):
    update_can_self_select = False
    related_fields_match_type = True

class MysqlDatabaseOperations(BaseDatabaseOperations):
    def date_extract_sql(self, lookup_type, field_name):
        # http://dev.mysql.com/doc/mysql/en/date-and-time-functions.html
        return "EXTRACT(%s FROM %s)" % (lookup_type.upper(), field_name)

    def date_trunc_sql(self, lookup_type, field_name):
        fields = ['year', 'month', 'day', 'hour', 'minute', 'second']
        format = ('%%Y-', '%%m', '-%%d', ' %%H:', '%%i', ':%%s') # Use double percents to escape.
        format_def = ('0000-', '01', '-01', ' 00:', '00', ':00')
        try:
            i = fields.index(lookup_type) + 1
        except ValueError:
            sql = field_name
        else:
            format_str = ''.join([f for f in format[:i]] + [f for f in format_def[i:]])
            sql = "CAST(DATE_FORMAT(%s, '%s') AS DATETIME)" % (field_name, format_str)
        return sql

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

    def no_limit_value(self):
        # 2**64 - 1, as recommended by the MySQL documentation
        return 18446744073709551615L

    def quote_name(self, name):
        if name.startswith("`") and name.endswith("`"):
            return name # Quoting once is enough.
        return "`%s`" % name

    def random_function_sql(self):
        return 'RAND()'

    def sql_flush(self, style, tables, sequences):
        # NB: The generated SQL below is specific to MySQL
        # 'TRUNCATE x;', 'TRUNCATE y;', 'TRUNCATE z;'... style SQL statements
        # to clear all tables of all data
        if tables:
            sql = ['SET FOREIGN_KEY_CHECKS = 0;']
            for table in tables:
                sql.append('%s %s;' % (style.SQL_KEYWORD('TRUNCATE'), style.SQL_FIELD(self.quote_name(table))))
            sql.append('SET FOREIGN_KEY_CHECKS = 1;')

            # 'ALTER TABLE table AUTO_INCREMENT = 1;'... style SQL statements
            # to reset sequence indices
            sql.extend(["%s %s %s %s %s;" % \
                (style.SQL_KEYWORD('ALTER'),
                 style.SQL_KEYWORD('TABLE'),
                 style.SQL_TABLE(self.quote_name(sequence['table'])),
                 style.SQL_KEYWORD('AUTO_INCREMENT'),
                 style.SQL_FIELD('= 1'),
                ) for sequence in sequences])
            return sql
        else:
            return []

    def value_to_db_datetime(self, value):
        if value is None:
            return None

        # MySQL doesn't support tz-aware datetimes
        if value.tzinfo is not None:
            raise ValueError("MySQL backend does not support timezone-aware datetimes.")

        # MySQL doesn't support microseconds
        return unicode(value.replace(microsecond=0))

    def value_to_db_time(self, value):
        if value is None:
            return None

        # MySQL doesn't support tz-aware datetimes
        if value.tzinfo is not None:
            raise ValueError("MySQL backend does not support timezone-aware datetimes.")

        # MySQL doesn't support microseconds
        return unicode(value.replace(microsecond=0))

    def year_lookup_bounds(self, value):
        # Again, no microseconds
        first = '%s-01-01 00:00:00'
        second = '%s-12-31 23:59:59.99'
        return [first % value, second % value]


class DatabaseOperations(zxJDBCOperationsMixin, MysqlDatabaseOperations):
    pass # The mixin contains all what is needed


class DatabaseWrapper(zxJDBCDatabaseWrapper):
    driver_class_name = 'com.mysql.jdbc.Driver'
    jdbc_url_pattern = \
        "jdbc:mysql://%(HOST)s%(PORT)s/%(NAME)s"
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
        self.ops = DatabaseOperations()
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation(self)

    def _cursor(self):
        if self.connection is None:
            self.connection = self.new_connection()
            # make transactions transparent to all cursors
            set_default_isolation_level(self.connection, innodb_binlog=True)
        real_cursor = self.connection.cursor()
        # Use the MySQL DataHandler for better compatibility:
        real_cursor.datahandler = MySQLDataHandler(real_cursor.datahandler)
        return CursorWrapper(real_cursor)


class CursorWrapper(zxJDBCCursorWrapper):
    def execute(self, *args, **kwargs):
        try:
            super(CursorWrapper, self).execute(*args, **kwargs)
        except Database.Error:
            # MySQL connections become unusable after an exception
            # occurs, unless the current transaction is rollback'ed.
            self.connection.rollback()
            raise
    def executemany(self, *args, **kwargs):
        try:
            super(CursorWrapper, self).executemany(*args, **kwargs)
        except Database.Error:
            # MySQL connections become unusable after an exception
            # occurs, unless the current transaction is rollback'ed.
            self.connection.rollback()
            raise
