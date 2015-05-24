# -*- coding: utf-8 -*-

from django.db.models.sql import compiler
from django.db.models.aggregates import Count


class SQLCompiler(compiler.SQLCompiler):

    def compile(self, node, select_format=False):
        vendor_impl = getattr(node, 'as_' + self.connection.vendor, None)
        if vendor_impl:
            sql, params = vendor_impl(self, self.connection)
        else:
            sql, params = node.as_sql(self, self.connection)
            if isinstance(node, Count):
                sql = sql.replace('%s', '%s::varchar')
        if select_format and not self.subquery:
            return node.output_field.select_format(self, sql, params)
        return sql, params


class SQLInsertCompiler(compiler.SQLInsertCompiler, SQLCompiler):
    pass


class SQLDeleteCompiler(compiler.SQLDeleteCompiler, SQLCompiler):
    pass


class SQLUpdateCompiler(compiler.SQLUpdateCompiler, SQLCompiler):
    pass


class SQLAggregateCompiler(compiler.SQLAggregateCompiler, SQLCompiler):
    pass
