# -*- coding: utf-8 -*-

import codecs

from decimal import Decimal

from django.utils import six

from doj.db.backends import JDBCBaseDatabaseSchemaEditor as BaseDatabaseSchemaEditor


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):

    sql_create_sequence = "CREATE SEQUENCE %(sequence)s"
    sql_delete_sequence = "DROP SEQUENCE IF EXISTS %(sequence)s CASCADE"
    sql_set_sequence_max = "SELECT setval('%(sequence)s', MAX(%(column)s)) FROM %(table)s"

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

    def _alter_column_type_sql(self, table, column, type):
        """
        Makes ALTER TYPE with SERIAL make sense.
        """
        if type.lower() == "serial":
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
            return super(DatabaseSchemaEditor, self)._alter_column_type_sql(table, column, type)
