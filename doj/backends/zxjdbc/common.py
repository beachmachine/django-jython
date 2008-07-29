import datetime
from java.sql import Connection

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
def set_default_isolation_level(connection):
    jdbc_conn = connection.__connection__
    jdbc_conn.setTransactionIsolation(Connection.TRANSACTION_READ_COMMITTED)

