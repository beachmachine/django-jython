from django.db.backends import BaseDatabaseIntrospection
from com.ziclix.python.sql import zxJDBC as Database

SQL_AUTOFIELD = -777555

class DatabaseIntrospection(BaseDatabaseIntrospection):
    data_types_reverse = {
        SQL_AUTOFIELD:              'AutoField',
        Database.BIGINT:            'IntegerField',
        Database.BIT:               'BooleanField',
        Database.CHAR:              'CharField',
        Database.DECIMAL:           'DecimalField',
        Database.DOUBLE:            'FloatField',
        Database.FLOAT:             'FloatField',
        #Database.SQL_GUID:              'TextField',
        Database.INTEGER:           'IntegerField',
        #Database.LONGVARBINARY:     ,
        #Database.LONGVARCHAR:       ,
        Database.NUMERIC:           'DecimalField',
        Database.REAL:              'FloatField',
        Database.SMALLINT:          'SmallIntegerField',
        Database.TINYINT:           'SmallIntegerField',
        Database.DATETIME:          'DateField',
        Database.TIME:              'TimeField',
        Database.TIMESTAMP:         'DateTimeField',
        #Database.SQL_VARBINARY:         ,
        Database.VARCHAR:           'TextField',
        Database.NCHAR:             'CharField',
        Database.LONGNVARCHAR:      'TextField',
        Database.NVARCHAR:          'TextField',
    }

    def get_table_list(self, cursor):
        """
        Returns a list of table names in the current database.
        """
        # TABLES: http://msdn2.microsoft.com/en-us/library/ms186224.aspx

        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
        return [row[0] for row in cursor.fetchall()]


    def _is_auto_field(self, cursor, table_name, column_name):
        """
        Checks whether column is Identity
        """
        # COLUMNPROPERTY: http://msdn2.microsoft.com/en-us/library/ms174968.aspx

        cursor.execute("SELECT COLUMNPROPERTY(OBJECT_ID(%s), %s, 'IsIdentity')",
                         (self.connection.ops.quote_name(table_name), column_name))
        return cursor.fetchall()[0][0]

    def get_table_description(self, cursor, table_name, identity_check=True):
        """Returns a description of the table, with DB-API cursor.description interface.

        The 'auto_check' parameter has been added to the function argspec.
        If set to True, the function will check each of the table's fields for the
        IDENTITY property (the IDENTITY property is the MSSQL equivalent to an AutoField).

        When a field is found with an IDENTITY property, it is given a custom field number
        of SQL_AUTOFIELD, which maps to the 'AutoField' value in the DATA_TYPES_REVERSE dict.
        """

        columns = [[c[3], c[4], None, c[6], c[6], c[8], c[10]] for c in cursor.columns(table=table_name)]
        items = []
        for column in columns:
            if identity_check and self._is_auto_field(cursor, table_name, column[0]):
                column[1] = SQL_AUTOFIELD
            if column[1] == Database.NVARCHAR and column[3] < 4000:
                column[1] = Database.NCHAR
            items.append(column)
        return items

    def _name_to_index(self, cursor, table_name):
        """
        Returns a dictionary of {field_name: field_index} for the given table.
        Indexes are 0-based.
        """
        return dict([(d[0], i) for i, d in enumerate(self.get_table_description(cursor, table_name, identity_check=False))])

    def get_relations(self, cursor, table_name):
        """
        Returns a dictionary of {field_index: (field_index_other_table, other_table)}
        representing all relationships to the given table. Indexes are 0-based.
        """
        # CONSTRAINT_COLUMN_USAGE: http://msdn2.microsoft.com/en-us/library/ms174431.aspx
        # CONSTRAINT_TABLE_USAGE:  http://msdn2.microsoft.com/en-us/library/ms179883.aspx
        # REFERENTIAL_CONSTRAINTS: http://msdn2.microsoft.com/en-us/library/ms179987.aspx
        # TABLE_CONSTRAINTS:       http://msdn2.microsoft.com/en-us/library/ms181757.aspx

        table_index = self._name_to_index(cursor, table_name)
        sql = """
SELECT e.COLUMN_NAME AS column_name,
  c.TABLE_NAME AS referenced_table_name,
  d.COLUMN_NAME AS referenced_column_name
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS AS a
INNER JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS AS b
  ON a.CONSTRAINT_NAME = b.CONSTRAINT_NAME
INNER JOIN INFORMATION_SCHEMA.CONSTRAINT_TABLE_USAGE AS c
  ON b.UNIQUE_CONSTRAINT_NAME = c.CONSTRAINT_NAME
INNER JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE AS d
  ON c.CONSTRAINT_NAME = d.CONSTRAINT_NAME
INNER JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE AS e
  ON a.CONSTRAINT_NAME = e.CONSTRAINT_NAME
WHERE a.TABLE_NAME = %s AND a.CONSTRAINT_TYPE = 'FOREIGN KEY'"""
        cursor.execute(sql, (table_name,))
        return dict([(table_index[item[0]], (self._name_to_index(cursor, item[1])[item[2]], item[1]))
                     for item in cursor.fetchall()])

    def get_indexes(self, cursor, table_name):
        """
        Returns a dictionary of fieldname -> infodict for the given table,
        where each infodict is in the format:
            {'primary_key': boolean representing whether it's the primary key,
             'unique': boolean representing whether it's a unique index,
             'db_index': boolean representing whether it's a non-unique index}
        """
        # CONSTRAINT_COLUMN_USAGE: http://msdn2.microsoft.com/en-us/library/ms174431.aspx
        # TABLE_CONSTRAINTS: http://msdn2.microsoft.com/en-us/library/ms181757.aspx

        pk_uk_sql = """
SELECT b.COLUMN_NAME, a.CONSTRAINT_TYPE
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS AS a
INNER JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE AS b
  ON a.CONSTRAINT_NAME = b.CONSTRAINT_NAME AND a.TABLE_NAME = b.TABLE_NAME
WHERE a.TABLE_NAME = %s AND (CONSTRAINT_TYPE = 'PRIMARY KEY' OR CONSTRAINT_TYPE = 'UNIQUE')"""

        field_names = [item[0] for item in self.get_table_description(cursor, table_name, identity_check=False)]
        indexes, results = {}, {}
        cursor.execute(pk_uk_sql, (table_name,))
        data = cursor.fetchall()
        if data:
            results.update(data)

        if self.connection.sqlserver_version >= 2005:
            # non-unique, non-compound indexes, only in SS2005?
            ix_sql = """
SELECT DISTINCT c.name
FROM sys.columns c
INNER JOIN sys.index_columns ic
  ON ic.object_id = c.object_id AND ic.column_id = c.column_id
INNER JOIN sys.indexes ix
  ON ix.object_id = ic.object_id AND ix.index_id = ic.index_id
INNER JOIN sys.tables t
  ON t.object_id = ix.object_id
WHERE ix.object_id IN (
  SELECT ix.object_id
  FROM sys.indexes ix
  GROUP BY ix.object_id, ix.index_id
  HAVING count(1) = 1)
AND ix.is_primary_key = 0
AND ix.is_unique_constraint = 0
AND t.name = %s"""

            cursor.execute(ix_sql, (table_name,))
            for column in [r[0] for r in cursor.fetchall()]:
                if column not in results:
                    results[column] = 'IX'

        for field in field_names:
            val = results.get(field, None)
            indexes[field] = dict(primary_key=(val=='PRIMARY KEY'), unique=(val=='UNIQUE'), db_index=(val=='IX'))

        return indexes
