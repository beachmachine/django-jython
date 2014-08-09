# -*- coding: utf-8 -*-

import codecs

from decimal import Decimal

from django.utils import six
from django.db.models import NOT_PROVIDED

from doj.db.backends import JDBCBaseDatabaseSchemaEditor as BaseDatabaseSchemaEditor


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):

    sql_rename_table = "RENAME TABLE %(old_table)s TO %(new_table)s"

    sql_alter_column_null = "MODIFY %(column)s %(type)s NULL"
    sql_alter_column_not_null = "MODIFY %(column)s %(type)s NOT NULL"
    sql_alter_column_type = "MODIFY %(column)s %(type)s"
    sql_rename_column = "ALTER TABLE %(table)s CHANGE %(old_column)s %(new_column)s %(type)s"

    sql_delete_unique = "ALTER TABLE %(table)s DROP INDEX %(name)s"

    sql_create_fk = "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s FOREIGN KEY (%(column)s) REFERENCES %(to_table)s (%(to_column)s)"
    sql_delete_fk = "ALTER TABLE %(table)s DROP FOREIGN KEY %(name)s"

    sql_delete_index = "DROP INDEX %(name)s ON %(table)s"

    sql_delete_pk = "ALTER TABLE %(table)s DROP PRIMARY KEY"

    alter_string_set_null = 'MODIFY %(column)s %(type)s NULL;'
    alter_string_drop_null = 'MODIFY %(column)s %(type)s NOT NULL;'

    sql_create_pk = "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s PRIMARY KEY (%(columns)s)"
    sql_delete_pk = "ALTER TABLE %(table)s DROP PRIMARY KEY"

    def quote_value(self, value):
        if isinstance(value, type(True)):
            return str(int(value))
        elif isinstance(value, (Decimal, float)):
            return str(value)
        elif isinstance(value, six.integer_types):
            return str(value)
        elif isinstance(value, six.string_types):
            return "\"%s\"" % six.text_type(value).replace("\"", "\\\"")
        elif value is None:
            return "NULL"
        elif isinstance(value, (bytes, bytearray, six.memoryview)):
            value = bytes(value)
            hex_encoder = codecs.getencoder('hex_codec')
            value_hex, _length = hex_encoder(value)
            # Use 'ascii' encoding for b'01' => '01', no need to use force_text here.
            return "X'%s'" % value_hex.decode('ascii').upper()
        else:
            raise ValueError("Cannot quote parameter value %r of type %s" % (value, type(value)))

    def skip_default(self, field):
        """
        MySQL doesn't accept default values for longtext and longblob
        and implicitly treats these columns as nullable.
        """
        return field.db_type(self.connection) in {'longtext', 'longblob'}

    def add_field(self, model, field):
        super(DatabaseSchemaEditor, self).add_field(model, field)

        # Simulate the effect of a one-off default.
        if self.skip_default(field) and field.default not in {None, NOT_PROVIDED}:
            effective_default = self.effective_default(field)
            self.execute('UPDATE %(table)s SET %(column)s = %%s' % {
                'table': self.quote_name(model._meta.db_table),
                'column': self.quote_name(field.column),
            }, [effective_default])
