"""
jTDS/MSSQL2005 database backend for Django.
"""
from datetime import date, datetime

try:
    # Force the database driver to load
    from java.lang import Class
    cls = Class.forName("net.sourceforge.jtds.jdbc.Driver").newInstance()
    from pool import ManualPoolingDriver
    from com.ziclix.python.sql import zxJDBC as Database
    from com.ziclix.python.sql import zxJDBC
    from com.ziclix.python.sql import PyStatement, PyExtendedCursor, PyCursor, PyConnection
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading zxJDBC module: %s" % e)

from django.db.backends import BaseDatabaseWrapper, BaseDatabaseFeatures, BaseDatabaseValidation
from doj.backends.zxjdbc.common import zxJDBCDatabaseWrapper, zxJDBCCursorWrapper
from django.db.backends.signals import connection_created
from django.conf import settings

# unchecked imports
from operations import DatabaseOperations
from client import DatabaseClient
from creation import DatabaseCreation
from introspection import DatabaseIntrospection

import os
import warnings

warnings.filterwarnings('error', 'The DATABASE_ODBC.+ is deprecated',DeprecationWarning, __name__, 0)

DatabaseError = zxJDBC.DatabaseError
IntegrityError = zxJDBC.IntegrityError


class DatabaseFeatures(BaseDatabaseFeatures):
    uses_custom_query_class = True
    can_use_chunked_reads = False
    can_return_id_from_insert = True
    #uses_savepoints = True


class DatabaseWrapper(zxJDBCDatabaseWrapper):
    MARS_Connection = False
    unicode_results = False

    # Collations:       http://msdn2.microsoft.com/en-us/library/ms184391.aspx
    #                   http://msdn2.microsoft.com/en-us/library/ms179886.aspx
    # T-SQL LIKE:       http://msdn2.microsoft.com/en-us/library/ms179859.aspx
    # Full-Text search: http://msdn2.microsoft.com/en-us/library/ms142571.aspx
    #   CONTAINS:       http://msdn2.microsoft.com/en-us/library/ms187787.aspx
    #   FREETEXT:       http://msdn2.microsoft.com/en-us/library/ms176078.aspx

    # operators are set in the __init__ method
    operators = {}

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self._LAST_DATABASE_NAME = None
        self._db_count = 0
        self.connection = None

        self.MARS_Connection = self.settings_dict['OPTIONS'].get('MARS_Connection', False)
        self.unicode_results = self.settings_dict['OPTIONS'].get('unicode_results', False)
        self.collation = self.settings_dict['OPTIONS'].get('collation', 'Latin1_General_CI_AS')

        self.operators = {
            # Since '=' is used not only for string comparision there is no way
            # to make it case (in)sensitive. It will simply fallback to the
            # database collation.
            'exact': '= %s',
            'iexact': "= UPPER(%s)",
            'contains': "LIKE %s ESCAPE '\\' COLLATE " + self.collation,
            'icontains': "LIKE UPPER(%s) ESCAPE '\\' COLLATE "+ self.collation,
            'like': "LIKE %s ESCAPE '\\' COLLATE " + self.collation,
            'ilike': "LIKE UPPER(%s) ESCAPE '\\' COLLATE "+ self.collation,
            'gt': '> %s',
            'gte': '>= %s',
            'lt': '< %s',
            'lte': '<= %s',
            'startswith': "LIKE %s ESCAPE '\\' COLLATE " + self.collation,
            'endswith': "LIKE %s ESCAPE '\\' COLLATE " + self.collation,
            'istartswith': "LIKE UPPER(%s) ESCAPE '\\' COLLATE " + self.collation,
            'iendswith': "LIKE UPPER(%s) ESCAPE '\\' COLLATE " + self.collation,

            # TODO: remove, keep native T-SQL LIKE wildcards support
            # or use a "compatibility layer" and replace '*' with '%'
            # and '.' with '_'
            'regex': 'LIKE %s COLLATE ' + self.collation,
            'iregex': 'LIKE %s COLLATE ' + self.collation,

            # TODO: freetext, full-text contains...
        }

        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation(self)

    def _cursor(self):
        new_conn = False
        settings_dict = self.settings_dict
        if self.connection is None:
            new_conn = True
            self.connection = self.new_jndi_connection()
            if self.connection is None:
                pool_name = self._register_driver()
                if not settings_dict['NAME']:
                    from django.core.exceptions import ImproperlyConfigured
                    raise ImproperlyConfigured('You need to specify NAME in your Django settings file.')

                url='jdbc:apache:commons:dbcp:%s' % pool_name
                self.connection = Database.connect(url, None, None, 'org.apache.commons.dbcp.PoolingDriver')
                connection_created.send(sender=self.__class__)
        cursor = self.connection.cursor()
        if new_conn:
            # Set date format for the connection.
            cursor.execute("SET DATEFORMAT ymd; SET DATEFIRST 7")

            # SQL Server violates the SQL standard w.r.t handling NULL values in UNIQUE columns.
            # We work around this by creating schema bound views on tables with with nullable unique columns
            # but we need to modify the cursor to abort if the view has problems.
            # See http://blogs.msdn.com/sqlcat/archive/2005/12/20/506138.aspx
            cursor.execute("SET ARITHABORT ON")
            cursor.execute("SET CONCAT_NULL_YIELDS_NULL ON")
            cursor.execute("SET QUOTED_IDENTIFIER ON")
            cursor.execute("SET ANSI_NULLS ON")
            cursor.execute("SET ANSI_PADDING ON")
            cursor.execute("SET ANSI_WARNINGS ON")
            cursor.execute("SET NUMERIC_ROUNDABORT OFF")
            cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")

            # jTDS can't execute some sql like CREATE DATABASE etc. in
            # Multi-statement, so we need to commit the above SQL sentences to
            # avoid this

        return CursorWrapper(cursor)

    def _register_driver(self):
        # Configure the pooled connection driver
        if self._LAST_DATABASE_NAME == self.settings_dict['NAME']:
            return "jdbc_pool_%s" % self._db_count

        self._db_count += 1
        pool_name = "jdbc_pool_%s" % self._db_count

        db_dict = {
                'NAME': self.settings_dict['NAME'],
                'HOST': self.settings_dict['HOST'] or 'localhost',
                'PORT': self.settings_dict['PORT'] or 1433,
                }
        self.driver = ManualPoolingDriver("jdbc:jtds:sqlserver://%(HOST)s:%(PORT)s/%(NAME)s" % db_dict,
                                    self.settings_dict['USER'],
                                    self.settings_dict['PASSWORD'],
                                    pool_name,
                                    )
        self._LAST_DATABASE_NAME = self.settings_dict['NAME']

        return pool_name

class CursorWrapper(zxJDBCCursorWrapper):
    """
    A wrapper around the pyodbc's cursor that takes in account a) some pyodbc
    DB-API 2.0 implementation and b) some common ODBC driver particularities.
    """
    def __init__(self, cursor):
        self.cursor = cursor
        self.last_sql = ''
        self.last_params = ()

    def format_sql(self, sql, n_params=None):
        # zxjdbc uses '?' instead of '%s' as parameter placeholder.
        if n_params is not None:
            sql = sql % tuple('?'*n_params)
        elif "%s" in sql:
            sql = sql.replace('%s', '?')
        return sql

    def format_params(self, params):
        fp = []
        for p in params:
            if isinstance(p, unicode) or isinstance(p, str):
                fp.append(p)
            elif isinstance(p, bool):
                if p:
                    fp.append(1)
                else:
                    fp.append(0)
            else:
                fp.append(p)
        return tuple(fp)

    def execute(self, sql, params=()):
        self.last_sql = sql
        sql = self.format_sql(sql, len(params))
        params = self.format_params(params)
        self.last_params = params
        return self.cursor.execute(sql, params)

    def executemany(self, sql, params_list):
        sql = self.format_sql(sql)
        # zxjdbc's cursor.executemany() doesn't support an empty param_list
        if not params_list:
            if '?' in sql:
                return
        else:
            raw_pll = params_list
            params_list = [self.format_params(p) for p in raw_pll]
        return self.cursor.executemany(sql, params_list)

    def format_results(self, rows):
        """
        Decode data coming from the database if needed and convert rows to tuples
        (zxJDBC Rows are not sliceable).
        """
        fr = []
        for row in rows:
            fr.append(row)
        return tuple(fr)

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is not None:
            return self.format_results(row)
        return []

    def fetchmany(self, chunk):
        return [self.format_results(row) for row in self.cursor.fetchmany(chunk)]

    def fetchall(self):
        return [self.format_results(row) for row in self.cursor.fetchall()]
