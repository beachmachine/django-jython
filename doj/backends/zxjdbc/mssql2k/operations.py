from django.db.backends import BaseDatabaseOperations
import datetime
import time

import query

class DatabaseOperations(BaseDatabaseOperations):
    # Define the parts of an ODBC date string
    # so we can do substring operations to match
    DATE_PARTS = {'year': (1,4),
              'month': (6,2),
              'day': (9,2)}

    def regex_lookup(self, lookup_type):
        """
        Returns the string to use in a query when performing regular expression
        lookups (using "regex" or "iregex"). The resulting string should
        contain a '%s' placeholder for the column being searched against.

        If the feature is not supported (or part of it is not supported), a
        NotImplementedError exception can be raised.
        """
        if lookup_type == 'regex':
            ignore_case = 0
        else:
            ignore_case = 1

        return "dbo.regex(%%s, %%s, %s) = 1" % ignore_case

    def start_transaction_sql(self):
        """
        Returns the SQL statement required to start a transaction.
        """
        return "BEGIN TRANSACTION"

    def date_extract_sql(self, lookup_type, field_name):

        start, end = self.DATE_PARTS[lookup_type]
        return "CONVERT(INT, SUBSTRING(%s, %s, %s))" % (self.quote_name(field_name), start, end)

    def _unquote_fieldname(self, fieldname):
        '''
        Try to unquote the fieldname so that SQL Server doesn't assign a
        weird semi-random name to the converted column.

        We *only* return the column name part though - we drop the table name.

        This method is really only used by the date_trunc_sql method and isn't meant
        for any other use.
        '''
        assert fieldname.startswith('[') and fieldname.endswith(']')
        short_name = fieldname.split('.')[-1][1:-1]
        return short_name

    def date_trunc_sql(self, lookup_type, field_name):
    	quoted_field_name = self.quote_name(field_name)

        short_name = self.quote_name(self._unquote_fieldname(quoted_field_name))

        sql_dict = {'name': quoted_field_name, 'short_name': short_name}

        if lookup_type == 'year':
            return "CONVERT(datetime, CONVERT(varchar, DATEPART(year, %(name)s)) + '/01/01') AS %(short_name)s" % sql_dict

        if lookup_type == 'month':
            return "CONVERT(datetime, CONVERT(varchar, DATEPART(year, %(name)s)) + '/' + CONVERT(varchar, DATEPART(month, %(name)s)) + '/01') AS %(short_name)s" %\
                    sql_dict

        if lookup_type == 'day':
            return "CONVERT(datetime, CONVERT(varchar(12), %(name)s)) AS %(short_name)s" % sql_dict

    def last_insert_id(self, cursor, table_name, pk_name):
        cursor.execute("SELECT CAST(IDENT_CURRENT(%s) AS bigint)", [self.quote_name(table_name)])
        return cursor.fetchone()[0]

    def no_limit_value(self):
        return None

    def prep_for_like_query(self, x):
        """Prepares a value for use in a LIKE query."""
        from django.utils.encoding import smart_unicode
        return (
            smart_unicode(x).\
                replace("\\", "\\\\").\
                replace("%", "\%").\
                replace("_", "\_").\
                replace("[", "\[").\
                replace("]", "\]")
            )

    def query_class(self, DefaultQueryClass):
        return query.query_class(DefaultQueryClass)

    def quote_name(self, name):
        if 'CONVERT(' in name:
            # SQL Server has a fragile parser.  If we'v already applied CONVERT on a column, treat this
            # column as pre-quoted.  No - it doesn't make any sense.  Don't think too hard about this.
            return name
        if name.startswith('[') and name.endswith(']'):
            return name # already quoted
        return '[%s]' % name

    def random_function_sql(self):
        return 'RAND()'

    def sql_flush(self, style, tables, sequences):
        """
        Returns a list of SQL statements required to remove all data from
        the given database tables (without actually removing the tables
        themselves).

        The `style` argument is a Style object as returned by either
        color_style() or no_style() in django.core.management.color.
        
        Originally taken from django-pyodbc project.
        """
        if not tables:
            return list()
            
        qn = self.quote_name
            
        # Cannot use TRUNCATE on tables that are referenced by a FOREIGN KEY; use DELETE instead.
        # (which is slow)
        from django.db import connection
        cursor = connection.cursor()
        # Try to minimize the risks of the braindeaded inconsistency in
        # DBCC CHEKIDENT(table, RESEED, n) behavior.
        seqs = []
        for seq in sequences:
            cursor.execute("SELECT COUNT(*) FROM %s" % qn(seq["table"]))
            rowcnt = cursor.fetchone()[0]
            elem = dict()

            if rowcnt:
                elem['start_id'] = 0
            else:
                elem['start_id'] = 1

            elem.update(seq)
            seqs.append(elem)

        cursor.execute("SELECT TABLE_NAME, CONSTRAINT_NAME FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS")
        fks = cursor.fetchall()
        
        sql_list = list()

        # Turn off constraints.
        sql_list.extend(['ALTER TABLE %s NOCHECK CONSTRAINT %s;' % (
            qn(fk[0]), qn(fk[1])) for fk in fks])

        # Delete data from tables.
        sql_list.extend(['%s %s %s;' % (
            style.SQL_KEYWORD('DELETE'), 
            style.SQL_KEYWORD('FROM'), 
            style.SQL_FIELD(qn(t))
            ) for t in tables])

        # Reset the counters on each table.
        sql_list.extend(['%s %s (%s, %s, %s) %s %s;' % (
            style.SQL_KEYWORD('DBCC'),
            style.SQL_KEYWORD('CHECKIDENT'),
            style.SQL_FIELD(qn(seq["table"])),
            style.SQL_KEYWORD('RESEED'),
            style.SQL_FIELD('%d' % seq['start_id']),
            style.SQL_KEYWORD('WITH'),
            style.SQL_KEYWORD('NO_INFOMSGS'),
            ) for seq in seqs])

        # Turn constraints back on.
        sql_list.extend(['ALTER TABLE %s CHECK CONSTRAINT %s;' % (
            qn(fk[0]), qn(fk[1])) for fk in fks])

        return sql_list

    def tablespace_sql(self, tablespace, inline=False):
        return "ON %s" % self.quote_name(tablespace)
        
    def value_to_db_datetime(self, value):
        if value is None:
            return None
            
        if value.tzinfo is not None:
            raise ValueError("SQL Server 2005 does not support timezone-aware datetimes.")

        # SQL Server 2005 doesn't support microseconds
        return value.replace(microsecond=0)
    
    def value_to_db_time(self, value):
        # MS SQL 2005 doesn't support microseconds
        #...but it also doesn't really suport bare times
        if value is None:
            return None
        return value.replace(microsecond=0)
	        
    def value_to_db_decimal(self, value, max_digits, decimal_places):
        if value is None or value == '':
            return None
        return value # Should be a decimal type (or string)

    def year_lookup_bounds(self, value):
        """
        Returns a two-elements list with the lower and upper bound to be used
        with a BETWEEN operator to query a field value using a year lookup

        `value` is an int, containing the looked-up year.
        """
        first = '%s-01-01 00:00:00'
        second = '%s-12-31 23:59:59'
        return [first % value, second % value]

    def field_cast_sql(self, db_type):
        """
        Given a column type (e.g. 'BLOB', 'VARCHAR'), returns the SQL necessary
        to cast it before using it in a WHERE statement. Note that the
        resulting string should contain a '%s' placeholder for the column being
        searched against.
        """
        if db_type is None:
            return '%s'

        if 'DATETIME' == db_type.upper():
            # We need to convert date and datetime columns into
            # ODBC canonical format.
            # See: http://msdn.microsoft.com/en-us/library/ms187928.aspx
            return "CONVERT(varchar, %s, 120)"
        elif 'SMALLDATETIME' == db_type.upper():
            return "SUBSTRING(CONVERT(varchar, %s, 120), 1, 10)"
        return '%s'


