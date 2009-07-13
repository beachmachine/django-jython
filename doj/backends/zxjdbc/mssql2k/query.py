"""Custom Query class for MS SQL Serever."""

# query_class returns the base class to use for Django queries.
# The custom 'SqlServerQuery' class derives from django.db.models.sql.query.Query
# which is passed in as "QueryClass" by Django itself.
#
# SqlServerQuery overrides:
# ...insert queries to add "SET IDENTITY_INSERT" if needed.
# ...select queries to emulate LIMIT/OFFSET for sliced queries.

#DEBUG=True
DEBUG=False

import string

# Cache. Maps default query class to new SqlServer query class.
_classes = {}


from com.ziclix.python.sql import PyStatement, PyExtendedCursor, PyCursor
from java.sql import Types


def query_class(QueryClass):
    """Return a custom Query subclass for SQL Server."""
    class SqlServerQuery(QueryClass):
        def __init__(self, *args, **kwargs):
            super(SqlServerQuery, self).__init__(*args, **kwargs)

            # If we are an insert query, wrap "as_sql"
            if self.__class__.__name__ == "InsertQuery":
                self._parent_as_sql = self.as_sql
                self.as_sql = self._insert_as_sql

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

        def get_primary_keys(self):
            return set([f for f in self.model._meta.fields if f.primary_key])

        def resolve_columns(self, row, fields=()):
            """
            Cater for the fact that SQL Server has no separate Date and Time
            data types.
            """
            from django.db.models.fields import DateField, DateTimeField, \
                TimeField, BooleanField, NullBooleanField
            values = []
            for value, field in map(None, row, fields):
                if value is not None:
                    if isinstance(field, DateTimeField):
                        # DateTimeField subclasses DateField so must be checked
                        # first.
                        pass # do nothing
                    elif isinstance(field, DateField):
                        value = value.date() # extract date
                    elif isinstance(field, TimeField):
                        value = value.time() # extract time
                    elif isinstance(field, (BooleanField, NullBooleanField)):
                        if value in (1,'t','True','1',True):
                            value = True
                        else:
                            value = False
                values.append(value)
            return values
            
        def as_sql(self, with_limits=True, with_col_aliases=False):
            """
            """
            # By default, just build the result and params with the superclass results

            sql, params = super(SqlServerQuery, self).as_sql(with_limits=False,
                    with_col_aliases=with_col_aliases)

            # Now comes the tricky part, we need to specialize the query to work against SQL Server 2k

            # Stuff to watch for
            if DEBUG:
                print "SQL              [%s] " % sql
                print "Params           [%s] " % str(params)
                print "High mark        [%s] " % self.high_mark
                print "Low mark         [%s] " % self.low_mark
                print "Distinct         [%s] " % self.distinct
                print "With Limits      [%s] " % with_limits
                print "With col aliases [%s] " % with_col_aliases
                print "Columns          [%s] " % self.get_columns(with_col_aliases)
                print "Ordering         [%s] " % self.get_ordering()


            if self.high_mark or self.low_mark:
                # Ok, we do a lot of finagling here just to get pagination
                cstmt = self._setup_pagination(sql, params, with_limits, with_col_aliases, \
                                self.low_mark, self.high_mark)
                sql, params = PyStatement(cstmt, '', PyStatement.STATEMENT_PREPARED), ()
            return sql, params

        def _insert_as_sql(self, *args, **kwargs):
            meta = self.get_meta()

            quoted_table = self.connection.ops.quote_name(meta.db_table)
            # Get (sql,params) from original InsertQuery.as_sql
            sql, params = self._parent_as_sql(*args,**kwargs)

            if (meta.pk.attname in self.columns) and (meta.pk.__class__.__name__ == "AutoField"):
                # check if only have pk and default value
                if len(self.columns)==1 and len(params)==0:
                    sql = "INSERT INTO %s DEFAULT VALUES" % quoted_table
                else:
                    sql = "SET IDENTITY_INSERT %s ON;%s;SET IDENTITY_INSERT %s OFF" %\
                        (quoted_table, sql, quoted_table)

            return sql, params

        def clone(self, klass=None, **kwargs):
            # Just use the parent clone - don't specialize any queries
            result = super(SqlServerQuery, self).clone(klass, **kwargs)
            return result

        def execute_sql(self, result_type='multi'):
            """
            Run the query against the database and returns the result(s). The
            return value is a single data item if result_type is SINGLE, or an
            iterator over the results if the result_type is MULTI.

            result_type is either MULTI (use fetchmany() to retrieve all rows),
            SINGLE (only retrieve a single row), or None (no results expected, but
            the cursor is returned, since it's used by subclasses such as
            InsertQuery).
            """
            from django.db.models.sql.constants import MULTI, SINGLE, GET_ITERATOR_CHUNK_SIZE

            if self.high_mark and self.high_mark <= self.low_mark:
                # Short circuit if we're slicing nothing
                return []

            # Pull in these imports from main Django DB
            # code base, but we can't import at the top level
            # or else we get circular imports 
            from django.db.models.sql.datastructures import EmptyResultSet
            from django.db.models.sql.query import empty_iter
            try:
                sql, params = self.as_sql()
                if not sql:
                    raise EmptyResultSet
            except EmptyResultSet:
                if result_type == MULTI:
                    return empty_iter()
                else:
                    return

            cursor = self.connection.cursor()
            if isinstance(sql, PyStatement):
                # We sometimes need to override with a PyStatement because
                # it's the only way to implement paginated results
                pycur = cursor
                while not isinstance(pycur, PyCursor):
                    pycur = pycur.cursor
                sql.execute(pycur, None, None)
            else:
                if DEBUG:
                    print sql, params
                cursor.execute(sql, params)

            if not result_type:
                return cursor
            if result_type == SINGLE:
                if self.ordering_aliases:
                    return cursor.fetchone()[:-len(self.ordering_aliases)]
                return cursor.fetchone()

            # The MULTI case.
            if self.ordering_aliases:
                from django.db.models.sql.query import order_modified_iter
                result = order_modified_iter(cursor, len(self.ordering_aliases),
                        self.connection.features.empty_fetchmany_value)
            else:
                result = iter((lambda: cursor.fetchmany(GET_ITERATOR_CHUNK_SIZE)),
                        self.connection.features.empty_fetchmany_value)

            # Need to serialize all the results because we don't want to maintain
            # state between requests
            result = list(result)

            # Force the PyStatement to close if we ever created one
            if isinstance(sql, PyStatement):
                sql.close()
                # Drop the temp table
                cur = self.connection.cursor()
                cur.execute("drop table #temp_table")
                cur.close()

            return result

        def get_ordering(self):
            result = super(SqlServerQuery, self).get_ordering()
            if self.ordering_aliases and self.distinct:
                # Clear ordering aliases if we're using a distinct query.
                # Ordering aliases will just screw things up 
                self.ordering_aliases = []
            return result

        def _setup_pagination(self, sql, params, with_limits, with_col_aliases, \
                                low_mark, high_mark):

            # Ok, got the column labels, now extract the type information by running the query *twice*
            # Yes, horribly inefficient, but how are you really going to handle all the bizarre corner
            # cases for SQL mangling?
            shim_sql = self._get_temp_table_cols(sql, params)

            # Ok, so we need to obtain the raw JDBC connection, create a prepared statement
            # and append the ORDERING_
            cursor = self.connection.cursor()

            jconn = cursor.cursor.connection.__connection__

            cstmt = jconn.prepareCall("returnpage(?, ?, ?, ?)");
            cstmt.setString('@query', shim_sql)
            cstmt.setString('@orderby', "djy_sql2k_sort_id ASC")

            # The *only* ordering alias we care about during pagination since we are 
            # forcing the output of the original SQL select to go into 

            self.ordering_aliases = ['djy_sql2k_sort_id']
            from django.db.models.sql.constants import GET_ITERATOR_CHUNK_SIZE
            if low_mark and high_mark:
                low, high = low_mark +1, high_mark
            elif low_mark:
                # We limit the upper bound to GET_ITERATOR_CHUNK_SIZE number of records or
                # else we risk SQL2k throwing us an instance of java.sql.DataTruncation
                low, high = low_mark +1, GET_ITERATOR_CHUNK_SIZE+(low_mark+1)
            elif high_mark:
                low, high = 1, high_mark
            else:
                raise RuntimeError, "Can't paginate when we have no low or high marks!"

            cstmt.setInt('@startrow', low)
            cstmt.setInt('@endrow', high)
            if DEBUG:
                print "Shim SQL : ", shim_sql
                print "Low mark : ", low
                print "High mark: ", high
            return cstmt

        def _get_temp_table_cols(self, sql, params):
            '''
            I'm sure there's a *good* way of doing this, but here's a bad way of doing it that works. :)
            '''
            cursor = self.connection.cursor()

            pycur = cursor
            while not isinstance(pycur, PyCursor):
                pycur = pycur.cursor
            jconn = pycur.connection.__connection__
            if params:
                j_sql = sql.replace("%s", '?')
            else:
                j_sql = sql
            j_pstmt = jconn.prepareStatement(j_sql)
            if params:
                # handle parameters
                from base import coerce_sql2k_type
                for i in range(len(params)):
                    param_obj = coerce_sql2k_type(params[i])
                    j_pstmt.setObject(i+1, param_obj)
            if DEBUG:
                print "JDBC statement: ", j_sql
                print "JDBC Params: ", params
            j_pstmt.execute()
            rset = j_pstmt.getResultSet()
            meta = rset.getMetaData()
            col_count = meta.getColumnCount()

            # Generate the (table_alias, col_alias) tuple list

            col_tuples = extract_colnames(j_sql)

            col_defs = []
            for col_num in range(1, col_count+1):
                col_dict = {}
                col_dict['table_alias'] = col_tuples[col_num-1][0]
                col_dict['label'] = meta.getColumnLabel(col_num)
                col_dict['name'] = meta.getColumnName(col_num).replace("-", '__')
                col_dict['sql_type'] = meta.getColumnTypeName(col_num)
                col_dict['prec'] = meta.getPrecision(col_num)
                col_dict['scale'] = meta.getScale(col_num)
                col_dict['nullable'] = meta.isNullable(col_num) == 1

                if col_dict['sql_type'] == 'ntext' and col_dict['prec'] > 8000:
                    # This looks like a dodgy declaration - just force it to be blank
                    # and let SQL Server use the default size
                    col_dict['prec'] = ''

                col_defs.append(col_dict)
            rset.close()
            j_pstmt.close()

            # Now - reconstitute the table defintion based on the column definition
            col_sql = []
            # Note that we have _0xdj_ between the table alias and colname.  Use that to coerce the values back
            reverse_types = {
                    'int': "%(table_alias)s_0xdj_%(name)s int " ,
                    'bit': '%(table_alias)s_0xdj_%(name)s bit ',
                    'datetime': "%(table_alias)s_0xdj_%(name)s %(sql_type)s " ,
                    'smalldatetime': "%(table_alias)s_0xdj_%(name)s %(sql_type)s " ,
                    'numeric': "%(table_alias)s_0xdj_%(name)s %(sql_type)s (%(prec)s, %(scale)s) " ,
                    'double': "%(table_alias)s_0xdj_%(name)s double precision " ,
                    'smallint': "%(table_alias)s_0xdj_%(name)s int " ,
                    'nvarchar': "%(table_alias)s_0xdj_%(name)s %(sql_type)s (%(prec)s) COLLATE SQL_Latin1_General_CP1_CI_AS " ,
                    'ntext': "%(table_alias)s_0xdj_%(name)s %(sql_type)s (%(prec)s) COLLATE SQL_Latin1_General_CP1_CI_AS " ,
                    }

            for cdef in col_defs:
                key = cdef['sql_type'].split()[0]
                value = reverse_types[key]
                if key == 'ntext' and cdef['prec'] == '':
                    # Drop the brackets around the ntext size declaration
                    value = "%(table_alias)s_0xdj_%(name)s %(sql_type)s COLLATE SQL_Latin1_General_CP1_CI_AS " 

                fragment = value % cdef

                if cdef['nullable']:
                    fragment += "NULL "
                else:
                    fragment += "NOT NULL "

                col_sql.append(fragment)

            table_sql = '''
            CREATE TABLE #temp_table ( 
                djy_sql2k_sort_id int IDENTITY (1, 1) NOT NULL,
                %s
            ) 
            ''' % ', \n'.join(col_sql)

            create_cur = self.connection.cursor()
            if DEBUG:
                print table_sql
            create_cur.execute(table_sql)
            create_cur.close()

            shim_cur = self.connection.cursor()
            shim_col_names = ', '.join(["%s_0xdj_%s" % (cdef['table_alias'], cdef['name']) for cdef in col_defs])
            shim_sql = "insert into #temp_table (%s) %s" % (shim_col_names, sql)
            if DEBUG:
                print "Insertion SQL: ", shim_sql
                print "Insertion Params: ", params
            shim_cur.execute(shim_sql, params)
            shim_cur.close()

            select_sql = "select %s, djy_sql2k_sort_id from #temp_table" % shim_col_names
            if DEBUG:
                print "Select SQL: ", select_sql

            return select_sql

    _classes[QueryClass] = SqlServerQuery
    return SqlServerQuery


def extract_colnames(j_sql):
    '''
    Return 2-tuples of (table_alias, col_name)
    '''
    j_sql = j_sql.replace("SELECT ",'').strip()
    j_sql = j_sql.replace("DISTINCT ",'').strip()
    j_sql = j_sql[:j_sql.find(" FROM")]
    return _tuplize(_tokenize(j_sql))


def _tokenize(input):
    '''
    Tokenize input using brackets as a stack and commas to denote terminators
    '''

    stack = 0
    buffer = ''
    results = []
    for ch in input:
        if ch == ',' and stack == 0:
            results.append(buffer.strip())
            buffer = ''
            continue
        elif ch == '(':
            stack += 1
        elif ch == ')':
            stack -= 1
        buffer += ch
    results.append(buffer)
    return results

def _tuplize(col_names):
    result = []
    for cname in col_names:
        if ' AS ' in cname:
            col_alias = cname.split(' AS ')[-1].strip()
        else:
            col_alias= cname.strip()
        tuple = []
        if '.' in col_alias:
            for part in col_alias.split("."):
                if part.startswith("[") and part.endswith("]"):
                    tuple.append(part[1:-1])
                else:
                    tuple.append(part)
        else:
            tuple = ['', col_alias]

        result.append(tuple)
    return result
