# -*- coding: utf-8 -*-

import codecs

from decimal import Decimal

from django.utils import six

from doj.db.backends import JDBCBaseDatabaseSchemaEditor as BaseDatabaseSchemaEditor


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):

    sql_create_sequence = "CREATE SEQUENCE %(sequence)s"
    sql_delete_sequence = "DROP SEQUENCE IF EXISTS %(sequence)s CASCADE"
    sql_set_sequence_max = "SELECT setval('%(sequence)s', MAX(%(column)s)) FROM %(table)s"
    sql_create_varchar_index = "CREATE INDEX %(name)s ON %(table)s (%(columns)s varchar_pattern_ops)%(extra)s"
    sql_create_text_index = "CREATE INDEX %(name)s ON %(table)s (%(columns)s text_pattern_ops)%(extra)s"

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
            return "E'\\\\x%s'::bytea" % value_hex.decode('ascii').upper()
        else:
            raise ValueError("Cannot quote parameter value %r of type %s" % (value, type(value)))

    def _model_indexes_sql(self, model):
        output = super(DatabaseSchemaEditor, self)._model_indexes_sql(model)
        if not model._meta.managed or model._meta.proxy or model._meta.swapped:
            return output

        for field in model._meta.local_fields:
            db_type = field.db_type(connection=self.connection)
            if db_type is not None and (field.db_index or field.unique):
                # Fields with database column types of `varchar` and `text` need
                # a second index that specifies their operator class, which is
                # needed when performing correct LIKE queries outside the
                # C locale. See #12234.
                if db_type.startswith('varchar'):
                    output.append(self._create_index_sql(
                        model, [field], suffix='_like', sql=self.sql_create_varchar_index))
                elif db_type.startswith('text'):
                    output.append(self._create_index_sql(
                        model, [field], suffix='_like', sql=self.sql_create_text_index))
        return output

    def _alter_column_type_sql(self, table, old_field, new_field, new_type):
        """
        Makes ALTER TYPE with SERIAL make sense.
        """
        if new_type.lower() == "serial":
            column = new_field.column
            sequence_name = "%s_%s_seq" % (table, column)
            return (
                (
                    self.sql_alter_column_type % {
                        "column": self.quote_name(column),
                        "type": "integer",
                    },
                    [],
                ),
                [
                    (
                        self.sql_delete_sequence % {
                            "sequence": sequence_name,
                        },
                        [],
                    ),
                    (
                        self.sql_create_sequence % {
                            "sequence": sequence_name,
                        },
                        [],
                    ),
                    (
                        self.sql_alter_column % {
                            "table": table,
                            "changes": self.sql_alter_column_default % {
                                "column": column,
                                "default": "nextval('%s')" % sequence_name,
                            }
                        },
                        [],
                    ),
                    (
                        self.sql_set_sequence_max % {
                            "table": table,
                            "column": column,
                            "sequence": sequence_name,
                        },
                        [],
                    ),
                ],
            )
        else:
            return super(DatabaseSchemaEditor, self)._alter_column_type_sql(
                table, old_field, new_field, new_type
            )
