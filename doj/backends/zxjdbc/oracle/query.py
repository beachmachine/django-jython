"""
    Custom Query class for Oracle.
    Derived from: django.db.models.sql.query.Query
    
    """

import datetime
from django.db.backends import util

# Cache. Maps default query class to new Oracle query class.
_classes = {}

def query_class(QueryClass, Database):
    """
        Returns a custom django.db.models.sql.query.Query subclass that is
        appropriate for Oracle.
        
        The 'Database' module (cx_Oracle) is passed in here so that all the setup
        required to import it only needs to be done by the calling module.
        """
    global _classes
    try:
        return _classes[QueryClass]
    except KeyError:
        pass
    
    class OracleQuery(QueryClass):
        def __reduce__(self):
            """
                Enable pickling for this class (normal pickling handling doesn't
                work as Python can only pickle module-level classes by default).
                """
            if hasattr(QueryClass, '__getstate__'):
                assert hasattr(QueryClass, '__setstate__')
                data = self.__getstate__()
            else:
                data = self.__dict__
            return (unpickle_query_class, (QueryClass,), data)
        
        def resolve_columns(self, row, fields=()):
            # If this query has limit/offset information, then we expect the
            # first column to be an extra "_RN" column that we need to throw
            # away.
            if self.high_mark is not None or self.low_mark:
                rn_offset = 1
            else:
                rn_offset = 0
            index_start = rn_offset + len(self.extra_select.keys())
            values = [self.convert_values(v, None)
                      for v in row[rn_offset:index_start]]
            for value, field in map(None, row[index_start:], fields):
                values.append(self.convert_values(value, field))
            return tuple(values)
        
        #def resolve_columns(self, row, fields=()):
        #    index_start = len(self.extra_select.keys())
        #    values = [self.convert_values(v, type(v)) for v in row[:index_start]]
        #    for value, field in map(None, row[index_start:], fields):
        #        values.append(self.convert_values(value, field))
        #    return values
        
        def convert_values(self, value, field):
            from django.db.models.fields import DateField, DateTimeField, \
                TimeField, BooleanField, NullBooleanField, DecimalField, FloatField, Field
            
            # Oracle stores empty strings as null. We need to undo this in
            # order to adhere to the Django convention of using the empty
            # string instead of null, but only if the field accepts the
            # empty string.
            if value is None:
                pass
            elif value is None and isinstance(field, Field) and field.empty_strings_allowed:
                value = u''
            # Convert 1 or 0 to True or False
            elif isinstance(value, float):
                value = float(value)
            # Added 04-26-2009 to repair "Invalid literal for int() base 10" error
            elif isinstance(value,int):
                value = int(value)
            elif isinstance(value,unicode):
                value = unicode(value)
            elif field is not None and field.get_internal_type() == 'AutoField':
                value = int(float(value))
            elif value in (1, 0) and field is not None and field.get_internal_type() in ('BooleanField', 'NullBooleanField'):
                value = bool(value)
            # Force floats to the correct type
            elif field is not None and field.get_internal_type() == 'FloatField':
                value = float(value)
            # Convert floats to decimals
            elif field is not None and field.get_internal_type() == 'DecimalField':
                value = util.typecast_decimal(field.format_number(value))
            elif field is not None and field.get_internal_type() == 'SmallIntegerField':
                value = util.typecast_decimal(field.format_number(value))
            return value
        
        def as_sql(self, with_limits=True, with_col_aliases=False):
            """
                Creates the SQL for this query. Returns the SQL string and list
                of parameters.  This is overriden from the original Query class
                to handle the additional SQL Oracle requires to emulate LIMIT
                and OFFSET.
                
                If 'with_limits' is False, any limit/offset information is not
                included in the query.
                """
            
            # The `do_offset` flag indicates whether we need to construct
            # the SQL needed to use limit/offset with Oracle.
            do_offset = with_limits and (self.high_mark is not None
                                         or self.low_mark)
            if not do_offset:
                sql, params = super(OracleQuery, self).as_sql(with_limits=False,
                                                              with_col_aliases=with_col_aliases)
            else:
                # `get_columns` needs to be called before `get_ordering` to
                # populate `_select_alias`.
                sql, params = super(OracleQuery, self).as_sql(with_limits=False,
                                                              with_col_aliases=True)
                
                # Wrap the base query in an outer SELECT * with boundaries on
                # the "_RN" column.  This is the canonical way to emulate LIMIT
                # and OFFSET on Oracle.
                high_where = ''
                if self.high_mark is not None:
                    high_where = 'WHERE ROWNUM <= %d' % (self.high_mark,)
                sql = 'SELECT * FROM (SELECT ROWNUM AS "_RN", "_SUB".* FROM (%s) "_SUB" %s) WHERE "_RN" > %d' % (sql, high_where, self.low_mark)
            
            return sql, params
    
    #def set_limits(self, low=None, high=None):
    #    super(OracleQuery, self).set_limits(low, high)
    # We need to select the row number for the LIMIT/OFFSET sql.
    # A placeholder is added to extra_select now, because as_sql is
    # too late to be modifying extra_select.  However, the actual sql
    # depends on the ordering, so that is generated in as_sql.
    #    self.extra_select['_RN'] = ('1', '')
    
    #def clear_limits(self):
    #    super(OracleQuery, self).clear_limits()
    #    if '_RN' in self.extra_select:
    #        del self.extra_select['_RN']
    
    _classes[QueryClass] = OracleQuery
    return OracleQuery

def unpickle_query_class(QueryClass):
    """
        Utility function, called by Python's unpickling machinery, that handles
        unpickling of Oracle Query subclasses.
        """
    # XXX: Would be nice to not have any dependency on cx_Oracle here. Since
    # modules can't be pickled, we need a way to know to load the right module.
    from com.ziclix.python.sql import zxJDBC
    
    klass = query_class(QueryClass, zxJDBC)
    return klass.__new__(klass)
unpickle_query_class.__safe_for_unpickling__ = True
