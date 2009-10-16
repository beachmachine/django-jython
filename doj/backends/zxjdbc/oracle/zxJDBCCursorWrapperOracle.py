"""
    Author:  Josh Juneau

    Wrapper for Django-Jython Oracle implementation for zxJDBC calls
"""

try:
    from com.ziclix.python.sql import zxJDBC as Database
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading zxJDBC module: %s" % e)
    
from django.utils.encoding import smart_str, force_unicode
    
class zxJDBCCursorWrapperOracle(object):
    """
    A simple wrapper to do the "%s" -> "?" replacement before running zxJDBC's
    execute or executemany
    """
    def __init__(self, cursor):
        self.cursor = cursor
 
    def execute(self, sql, params=()):
        if params is None:
            params = []
        else:
            params = params
        if len(params) > 0:
            sql = sql % (('?',) * len(params))
        if sql.endswith(';') or sql.endswith('/'):
            sql = sql[:-1]
        self.cursor.execute(sql, params)
        
    def executemany(self, sql, param_list):
        if len(param_list) > 0:
            sql = sql % (('?',) * len(param_list[0]))
        self.cursor.executemany(sql, param_list)
        
    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return row
        return self._rowfactory(row)

    def fetchmany(self, size=None):
        if size is None:
            size = self.arraysize
        return tuple([self._rowfactory(r)
                      for r in self.cursor.fetchmany(size)])

    def fetchall(self):
        return tuple([self._rowfactory(r)
                      for r in self.cursor.fetchall()])

    def _rowfactory(self, row):
        # Cast numeric values as the appropriate Python type based upon the
        # cursor description, and convert strings to unicode.
        casted = []
        for value, desc in zip(row, self.cursor.description):
            # Altered on 04-26-2009 JJ
            # Changed 'is' to '==' for NUMBER comparison
          
            if value is not None and desc[1] == Database.NUMBER:
                
                precision, scale = desc[4:6]
                if scale == -127:
                    if precision == 0:
                        # NUMBER column: decimal-precision floating point
                        # This will normally be an integer from a sequence,
                        # but it could be a decimal value.
                        
                        if isinstance(value, float):
                            pass
                        else:
                            if '.' in value:
                                value = Decimal(value)
                            else:
                                value = int(value)
                    else:
                        # FLOAT column: binary-precision floating point.
                        # This comes from FloatField columns.
                        value = float(value)
                elif precision > 0:
                    # NUMBER(p,s) column: decimal-precision fixed point.
                    # This comes from IntField and DecimalField columns.
                    if scale == 0:
                        value = int(value)
                    else:
                        value = Decimal(value)
                else:
                    value = int(value)
            else:
                value = to_unicode(value)
            casted.append(value)
        return tuple(casted)
       


    def __getattr__(self, attr):
        return getattr(self.cursor, attr)
        
def to_unicode(s):
    """
    Convert strings to Unicode objects (and return all other data types
    unchanged).
    """
    if isinstance(s, basestring):
       return force_unicode(s)
    return s
