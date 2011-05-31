# -*- coding: utf-8 -*-
import datetime
from java.sql import Connection
from com.ziclix.python.sql import zxJDBC
from django.db.backends import BaseDatabaseWrapper

class zxJDBCDatabaseWrapper(BaseDatabaseWrapper):
    default_host = 'localhost'
    default_port = ''
    driver_class_name = None # Must be overriden
    jdbc_url_pattern = None # Must be overriden

    def __init__(self, *args, **kwargs):
        super(zxJDBCDatabaseWrapper, self).__init__(*args, **kwargs)

    def jdbc_url(self):
        return self.jdbc_url_pattern % self.settings_dict_postprocesed()

    def settings_dict_postprocesed(self):
        settings_dict = self.settings_dict.copy() # Avoid messing with the
                                                  # original settings
        host, port = settings_dict['HOST'], settings_dict['PORT']
        if not host:
            settings_dict['HOST'] = self.default_host
        if port:
            settings_dict['PORT'] = ":%s" % port
        elif self.default_port:
            settings_dict['PORT'] = ":%s" % self.default_port
        return settings_dict

    def new_connection(self):
        connection = self.new_jndi_connection()
        if not connection:
            settings_dict = self.settings_dict
            if settings_dict['NAME'] == '':
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured(
                    "You need to specify DATABASE NAME in your Django settings file.")
            connection = zxJDBC.connect(self.jdbc_url(),
                                        settings_dict['USER'],
                                        settings_dict['PASSWORD'],
                                        self.driver_class_name,
                                        **settings_dict['OPTIONS'])
        return connection
    
    def new_jndi_connection(self):
        """
        Returns a zxJDBC Connection object obtained from a JNDI data source if
        the settings dictionary contains the JNDI_NAME entry on the
        DATABASE_OPTIONS dictionary, or None if it doesn't.
        """
        settings_dict = self.settings_dict
        if 'DATABASE_OPTIONS' not in settings_dict: 
            return None
        if 'JNDI_NAME' not in settings_dict['DATABASE_OPTIONS']: 
            return None

        name = settings_dict['DATABASE_OPTIONS']['JNDI_NAME']
        props = settings_dict['DATABASE_OPTIONS'].get('JNDI_CONTEXT_OPTIONS', {})
        # Default the JNDI endpoint to a Glassfish instance
        # running on localhost
        #     jndi_endpoint = settings_dict['DATABASE_OPTIONS'].get('JNDI_ENDPOINT', 'localhost:3700')
        #     jndi_ctx_factory = settings_dict['DATABASE_OPTIONS'].get('JNDI_INITIAL_CONTEXT_FACTORY', 'localhost:3700')
        #     props = {'com.sun.appserv.iiop.endpoints':jndi_endpoint,
#              Context.INITIAL_CONTEXT_FACTORY:jndi_ctx_factory}
        return zxJDBC.lookup(name, keywords=props)


class zxJDBCOperationsMixin(object):
    # zxJDBC supports dates, times, datetimes and decimal directly
    def value_to_db_date(self, value):
        return value

    def value_to_db_datetime(self, value):
        return value

    def value_to_db_time(self, value):
        return value

    def value_to_db_decimal(self, value, max_digits, decimal_places):
        return value

    def year_lookup_bounds(self, value):
        first = datetime.datetime(value, 1, 1)
        second = datetime.datetime(value, 12, 31,
                                   23, 59, 59, 999999)
        return [first, second]


class zxJDBCFeaturesMixin(object):
    needs_datetime_string_cast = False


class zxJDBCCursorWrapper(object):
    """
    A simple wrapper to do the "%s" -> "?" replacement before running zxJDBC's
    execute or executemany
    """
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, sql, params=()):
        sql = sql % (('?',) * len(params))
        self.cursor.execute(sql, params)

    def executemany(self, sql, param_list):
        if len(param_list) > 0:
            sql = sql % (('?',) * len(param_list[0]))
        self.cursor.executemany(sql, param_list)

    def __getattr__(self, attr):
        return getattr(self.cursor, attr)

# Must be called by zxJDBC backends after instantiating a connection
def set_default_isolation_level(connection, innodb_binlog = False):
    jdbc_conn = connection.__connection__
    if innodb_binlog:
        jdbc_conn.setTransactionIsolation(Connection.TRANSACTION_REPEATABLE_READ)
    else:
        jdbc_conn.setTransactionIsolation(Connection.TRANSACTION_READ_COMMITTED)


