"""
jTDS/MSSQL database backend for Django.

Django uses this if the DATABASE_ENGINE setting is empty (None or empty string).

Each of these API functions, except connection.close(), raises
ImproperlyConfigured.
"""

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

from django.core.exceptions import ImproperlyConfigured
from django.db.backends import *
from django.db.backends import BaseDatabaseFeatures, BaseDatabaseValidation
from django.conf import settings
from pool import ManualPoolingDriver
from doj.backends.zxjdbc.common import zxJDBCDatabaseWrapper
from operations import DatabaseOperations
from introspection import DatabaseIntrospection
from creation import DatabaseCreation

if not hasattr(settings, "DATABASE_COLLATION"):
    settings.DATABASE_COLLATION = 'Latin1_General_CI_AS'

def complain(*args, **kwargs):
    raise ImproperlyConfigured, "You haven't set the DATABASE_ENGINE setting yet."

DatabaseError = zxJDBC.DatabaseError
IntegrityError = zxJDBC.IntegrityError

class DatabaseClient(BaseDatabaseClient):
    runshell = complain
    

class DatabaseWrapper(zxJDBCDatabaseWrapper):    
    jdbc_url_pattern = "jdbc:jtds:sqlserver://%(DATABASE_HOST)s%(DATABASE_PORT)s/%(DATABASE_NAME)s"
    driver_class_name = "net.sourceforge.jtds.jdbc.Driver"
    operators = {
        # Since '=' is used not only for string comparision there is no way
        # to make it case (in)sensitive. It will simply fallback to the
        # database collation.
        'exact': '= %s ',
        'iexact': "= UPPER(%s) ",
        'contains': "LIKE %s ESCAPE '\\' COLLATE " + settings.DATABASE_COLLATION,
        'icontains': "LIKE UPPER(%s) ESCAPE '\\' COLLATE "+ settings.DATABASE_COLLATION,
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': "LIKE %s ESCAPE '\\' COLLATE " + settings.DATABASE_COLLATION,
        'endswith': "LIKE %s ESCAPE '\\' COLLATE " + settings.DATABASE_COLLATION,
        'istartswith': "LIKE UPPER(%s) ESCAPE '\\' COLLATE " + settings.DATABASE_COLLATION,
        'iendswith': "LIKE UPPER(%s) ESCAPE '\\' COLLATE " + settings.DATABASE_COLLATION,
    }


    def _register_driver(self):
        # Configure the pooled connection driver
        if self._LAST_DATABASE_NAME == settings.DATABASE_NAME:
            return "jdbc_pool_%s" % self._db_count

        self._db_count += 1
        pool_name = "jdbc_pool_%s" % self._db_count

        db_dict = {
                'DATABASE_NAME': settings.DATABASE_NAME,
                'DATABASE_HOST': settings.DATABASE_HOST or 'localhost',
                'DATABASE_PORT': settings.DATABASE_PORT or 1433,
                }
        self.driver = ManualPoolingDriver("jdbc:jtds:sqlserver://%(DATABASE_HOST)s:%(DATABASE_PORT)s/%(DATABASE_NAME)s" % db_dict, 
                                    settings.DATABASE_USER, 
                                    settings.DATABASE_PASSWORD,
                                    pool_name,
                                    )
        self._LAST_DATABASE_NAME = settings.DATABASE_NAME

        return pool_name

    def _cursor(self, settings):
        '''
        Implementation specific cursor
        '''
        new_conn = False
        if self.connection is None:
            # TODO: Refactor this DBCP pool setup to zxJDBCCursorWrapper
            new_conn = True
            self.connection = self.new_jndi_connection()
            if self.connection is None:
                pool_name = self._register_driver()
                if not settings.DATABASE_NAME:
                    from django.core.exceptions import ImproperlyConfigured
                    raise ImproperlyConfigured("You need to specify DATABASE_NAME in your Django settings file.")
    
                url='jdbc:apache:commons:dbcp:%s' % pool_name
                self.connection = Database.connect(url, None, None, 'org.apache.commons.dbcp.PoolingDriver')

        cursor = self.connection.cursor()
        if new_conn:
            cursor.execute("SET DATEFORMAT ymd")

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

    def __init__(self, autocommit=False, **kwargs):
        super(DatabaseWrapper, self).__init__(autocommit=autocommit, **kwargs)
        self._LAST_DATABASE_NAME = None
        self.connection = None
        self._db_count = 0

        self.features = DatabaseFeatures()
        self.ops = DatabaseOperations()
        self.client = DatabaseClient()                      # XXX: No client is supported yet
        self.creation = DatabaseCreation(self)              # Basic type declarations for creating tables
        self.introspection = DatabaseIntrospection(self)    
        self.validation = BaseDatabaseValidation()          # XXX: No real database validation yet

class DatabaseFeatures(BaseDatabaseFeatures):
    uses_custom_query_class = True




class CursorWrapper(object):
    """
    A wrapper around the zxJDBC's cursor that takes in account some zxJDBC
    DB-API 2.0 implementation and common ODBC driver particularities.
    """
    def __init__(self, cursor):
        self.cursor = cursor

    def format_sql(self, sql):
        # zxjdbc uses '?' instead of '%s' as parameter placeholder.
        if "%s" in sql:
            sql = sql.replace('%s', '?')
        return sql

    def format_params(self, params):
        fp = []
        for p in params:
            p = coerce_sql2k_type(p)
            fp.append(p)
        return tuple(fp)

    def execute(self, sql, params=()):
        sql = self.format_sql(sql)
        params = self.format_params(params)
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
        (zxjdbc Rows are not sliceable).
        """
        fr = []
        for row in rows:
            fr.append(row)
        return tuple(fr)

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is not None:
            return self.format_results(row)
        return row

    def fetchmany(self, chunk):
        return [self.format_results(row) for row in self.cursor.fetchmany(chunk)]

    def fetchall(self):
        return [self.format_results(row) for row in self.cursor.fetchall()]

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            return getattr(self.cursor, attr)

def coerce_sql2k_type(p):
    '''
    Need to coerce some python types to jTDS friendly types
    so that PreparedStatement::setObject() can work properly
    '''
    if isinstance(p, type(True)):
        if p:
            return 1
        else:
            return 0
    elif isinstance(p, type(5L)):
        # zxJDBC doesn't like injecting long types, or maybe it
        # actually depends on the underlying SQL datatype..
        # Need to figure out a better fix for this
        if p == int(p):
            return int(p)
        else:
            raise RuntimeError, "SQL Serer 2000 +jTDS can't seem to handle long values. Found : [%s]" % p
    return p




