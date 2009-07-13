from django.db.backends.creation import BaseDatabaseCreation

class DatabaseCreation(BaseDatabaseCreation):
    '''
    Overloaded bits of the database creation code
    '''

    data_types = {
        'AutoField':         'int IDENTITY (1, 1)',
        'BooleanField':      'bit',
        'CharField':         'nvarchar(%(max_length)s)',
        'CommaSeparatedIntegerField': 'nvarchar(%(max_length)s)',
        'DateField':         'smalldatetime',
        'DateTimeField':     'datetime',
        'DecimalField':      'numeric(%(max_digits)s, %(decimal_places)s)',
        'FileField':         'nvarchar(%(max_length)s)',
        'FilePathField':     'nvarchar(%(max_length)s)',
        'FloatField':        'double precision',
        'IntegerField':      'int',
        'IPAddressField':    'nvarchar(15)',
        'NullBooleanField':  'bit',
        'OneToOneField':     'int',
        'PositiveIntegerField': 'int CHECK ([%(column)s] >= 0)',
        'PositiveSmallIntegerField': 'smallint CHECK ([%(column)s] >= 0)',
        'SlugField':         'nvarchar(%(max_length)s)',
        'SmallIntegerField': 'smallint',
        'TextField':         'ntext',
        'TimeField':         'datetime',
    }

    def __init__(self, connection):
        super(DatabaseCreation,self).__init__(connection)

        # Keep track of all unique nullable fields
        self.unique_fields = []

        # We need to keep track of all seen models and created models for
        # ourself so that we can properly generate all the constraint triggers
        self._seen_models = set()
        self._created_models = set()

        self._trigger_sql = set()

    def create_test_db(self, verbosity=1, autoclobber=False):
        result = super(DatabaseCreation, self).create_test_db(verbosity, autoclobber)

        # Force the SQL2k command to run now.
        from jtds.mssql2kext.management.commands import sql2kext 
        sql2kext.Command().handle_noargs()

        return result

    def _destroy_test_db(self, test_database_name, verbosity):
        cursor = self.connection.cursor()
        if not self.connection.connection.autocommit:
            self.connection.connection.commit()
        self.connection.connection.autocommit = True
        cursor.execute("ALTER DATABASE %s SET SINGLE_USER WITH ROLLBACK IMMEDIATE " % self.connection.ops.quote_name(test_database_name))
        cursor.execute("DROP DATABASE %s" %self.connection.ops.quote_name(test_database_name))
        self.connection.close()

    def sql_for_many_to_many(self, model, style):
        """
        We need to inject the trigger code for a model after all the tables for this application have been
        created.

        The code goes in this method only because it's known that the syncdb command in 
        django.core.management.commands.syncdb call this last.

        A better option would be to have a signal hook after all models have been
        created, but before the the applications are signalled so that the database 
        backend can respond to creation prior to individual applications respond.
        """
        final_output = super(DatabaseCreation, self).sql_for_many_to_many(model, style)
        from django.db import models
        opts = model._meta
        app_label = opts.app_label
        app = [app for app in models.get_apps() if app.__name__.split('.')[-2] == app_label][0]
        app_model_set = set(models.get_models(app))

        # Wait until the app_model_set is finished loading
        if app_model_set != (app_model_set & self._seen_models | set([model])):
            return final_output

        # This is the last model - we can safely assume it's ok to 
        # inject all the constraint trigger code now
        model_fkeys = {}
        for model in app_model_set:
            opts = model._meta
            model_fkeys[model] = []
            for f in opts.local_fields:
                if f.rel:
                    model_fkeys[model].append(f)

        qn = self.connection.ops.quote_name

        for model, model_keys in model_fkeys.items():
            sql_block = []
            # For each model, we want the list of all foreign keys
            # to clear out references to other objects
            # and to clear all references 
            tmpl = '''UPDATE %(table)s SET %(this_to_rel)s = NULL where %(this_pkey)s in (SELECT %(this_pkey)s from deleted)'''
            opts = model._meta
            table = opts.db_table
            this_pkey = [f for f in opts.local_fields if f.primary_key][0].column

            for model_f in model_keys:
                sql_dict = {'table': qn(table),
                            'this_to_rel': qn(model_f.column),
                            'this_pkey': qn(this_pkey),}
                if model_f.null:
                    sql_block.append(tmpl % sql_dict)

            # Generate all inbound relationships and clear the foreign keys
            for inbound_model in app_model_set:
                inbound_rels = [(inbound_model, f) for f in model_fkeys[inbound_model] if f.rel.to == model]
                for in_model, in_f in inbound_rels:
                    tmpl = '''UPDATE %(other_table)s SET %(fkey)s = NULL where %(fkey)s in (SELECT %(this_pkey)s from deleted)'''
                    rel_opts = in_model._meta
                    other_table = rel_opts.db_table
                    sql_dict = {'other_table': qn(other_table),
                                'fkey': qn(in_f.column),
                                'this_pkey': qn(this_pkey),
                                }
                    if in_f.null:
                        sql_block.append(tmpl % sql_dict)

            trigger_name = '%s_%x' % (table, abs(hash(table)))

            instead_of_sql = """
CREATE TRIGGER %(instead_trigger_name)s ON %(table)s 
INSTEAD OF DELETE
AS
BEGIN
%(sql)s
    DELETE FROM %(table)s WHERE %(this_pkey)s IN (SELECT %(this_pkey)s FROM deleted) 
print '%(escaped_sql)s'
END
;
            """ % { 
                    'instead_trigger_name': qn('instead_%s' % trigger_name),
                    'table': qn(table),
                    'sql': '\n'.join(['    %s' % stmt for stmt in sql_block]),
                    'escaped_sql': ('\n'.join(['    %s' % stmt for stmt in sql_block])).replace("'", "\\'"),
                    'this_pkey': qn(this_pkey),
                    }


            if instead_of_sql not in self._trigger_sql:
                # We only want to generate the instead trigger if there is an actual
                # code block
                if len(sql_block) <> 0:
                    self._trigger_sql.add(instead_of_sql)
                    final_output.append(instead_of_sql)

        return final_output

    def sql_for_pending_references(self, model, style, pending_references):
        """
        SQL Server 2000 needs to inject trigger code to emulate deferrable
        constraints.

        On object delete, we manually set the foreign keys to NULL with an
        INSTEAD OF DELETE trigger, and then actually delete the record in the
        AFTER DELETE trigger.

        If the columns are specified with NOT NULL constraints, the trigger will fail
        and will exhibit the correct behaviour.  If NULL is allowed, this will
        allow us to emulate DEFERRABLE constraints.

        Note that SQL Server 2000 will automatically delete triggers that are
        bound to tables when the table is dropped.
        """
        import copy
        # Make a shallow copy of the pending_references
        pending_references_orig = copy.copy(pending_references)

        final_output = super(DatabaseCreation, self).sql_for_pending_references(model, style, pending_references)

        return final_output

    def sql_create_model(self, model, style, known_models=set()):
        '''
        Returns the SQL required to create a single model, as a tuple of:
            (list_of_sql, pending_references_dict)

        overload this to create a view with SCHEMABINDING applied to the original table
        to support fields marked as unique and nullable

        The key differences between this and the super class implementation is that
        we do not generate unique constriants for nullable field types, or 
        unique_together fieldsets.
        '''

        self._seen_models.update(known_models)
        self._created_models.add(model)

        from django.db import models

        opts = model._meta
        final_output = []
        table_output = []
        pending_references = {}
        qn = self.connection.ops.quote_name
        for f in opts.local_fields:
            col_type = f.db_type()
            tablespace = f.db_tablespace or opts.db_tablespace
            if col_type is None:
                # Skip ManyToManyFields, because they're not represented as
                # database columns in this table.
                continue
            # Make the definition (e.g. 'foo VARCHAR(30)') for this field.
            field_output = [style.SQL_FIELD(qn(f.column)),
                style.SQL_COLTYPE(col_type)]
            field_output.append(style.SQL_KEYWORD('%sNULL' % (not f.null and 'NOT ' or '')))
            if f.primary_key:
                field_output.append(style.SQL_KEYWORD('PRIMARY KEY'))
            elif f.unique:
                if not f.null:
                    field_output.append(style.SQL_KEYWORD('UNIQUE'))
                self.unique_fields.append(f)

            if tablespace and f.unique:
                # We must specify the index tablespace inline, because we
                # won't be generating a CREATE INDEX statement for this field.
                field_output.append(self.connection.ops.tablespace_sql(tablespace, inline=True))
            if f.rel:
                ref_output, pending = self.sql_for_inline_foreign_key_references(f, known_models, style)
                if pending:
                    pr = pending_references.setdefault(f.rel.to, []).append((model, f))
                else:
                    field_output.extend(ref_output)
            table_output.append(' '.join(field_output))
        if opts.order_with_respect_to:
            table_output.append(style.SQL_FIELD(qn('_order')) + ' ' + \
                style.SQL_COLTYPE(models.IntegerField().db_type()) + ' ' + \
                style.SQL_KEYWORD('NULL'))

        for field_constraints in opts.unique_together:
            contraint_fields = [opts.get_field(f) for f in field_constraints]
            null_allowed = [f for f in contraint_fields if f.null]

            # Only do an inline UNIQUE constraint if none of the unique_together columns
            # allow nulls.  Otherwise - let the schemabinding hack build the unique index
            if len(null_allowed) == 0:
                table_output.append(style.SQL_KEYWORD('UNIQUE') + ' (%s)' % \
                    ", ".join([style.SQL_FIELD(qn(opts.get_field(f).column)) for f in field_constraints]))

        full_statement = [style.SQL_KEYWORD('CREATE TABLE') + ' ' + style.SQL_TABLE(qn(opts.db_table)) + ' (']
        for i, line in enumerate(table_output): # Combine and add commas.
            full_statement.append('    %s%s' % (line, i < len(table_output)-1 and ',' or ''))
        full_statement.append(')')
        if opts.db_tablespace:
            full_statement.append(self.connection.ops.tablespace_sql(opts.db_tablespace))
        full_statement.append(';')
        final_output.append('\n'.join(full_statement))

        if self.unique_fields:
            final_output.extend(self._create_schemabinding_view(style, opts))

        if opts.has_auto_field:
            # Add any extra SQL needed to support auto-incrementing primary keys.
            auto_column = opts.auto_field.db_column or opts.auto_field.name
            autoinc_sql = self.connection.ops.autoinc_sql(opts.db_table, auto_column)
            if autoinc_sql:
                for stmt in autoinc_sql:
                    final_output.append(stmt)

        return final_output, pending_references

    def _create_schemabinding_view(self, style, opts):
        '''
        Walk the list of unique_fields and generate a view to enforce
        uniqueness on 
        '''

        # Do a quick check to see if we have nullable and unique fields
        # defined
        if len([f for f in self.unique_fields if f.null and f.unique]) == 0:
            return []

        sql_stmts = []
        #sql_stmts.append("-- Start SCHEMABINDING hack for %s" % style.SQL_TABLE(qn(db_table)))

        db_table, local_fields = opts.db_table, opts.local_fields

        qn = self.connection.ops.quote_name

        d ={'view_name': style.SQL_TABLE(qn("%s_vw" % db_table)),
            'fields': ', \n    '.join(["    %s" % style.SQL_FIELD(qn(f.column)) for f in local_fields]),
            'table_name': style.SQL_TABLE(qn(db_table)),
            'null_parts': ' OR\n        '.join(['%s IS NOT NULL' % style.SQL_FIELD(qn(f.column)) for f in local_fields if f.null]),
            }


        sql_parts = []
        sql_parts.append("CREATE VIEW %(view_name)s WITH SCHEMABINDING " % d)
        sql_parts.append("    AS")
        sql_parts.append("    SELECT")
        sql_parts.append("    %(fields)s" % d)
        sql_parts.append("    FROM")
        sql_parts.append("        [dbo].%(table_name)s" % d)
        sql_parts.append("    WHERE")
        sql_parts.append("        %(null_parts)s" % d)

        sql_stmts.append('\n'.join(sql_parts))
        sql_parts = []


        # Now create all the indices
        unique_nullable = [f for f in local_fields if f.null and f.unique]
        for i, f in enumerate(unique_nullable):
            d ={'vidx_name' : style.SQL_TABLE(qn("%s_vidx_%s" % (db_table, i))),
                'idx_name' : style.SQL_TABLE(qn("%s_idx_%s" % (db_table, i))),
                'table_name': style.SQL_TABLE(qn(db_table)),
                'view_name': style.SQL_TABLE(qn("%s_vw" % db_table)),
                'col_name': style.SQL_FIELD(qn(f.column)),
                }
            if i == 0:
                sql_stmts.append("CREATE UNIQUE CLUSTERED INDEX %(vidx_name)s on %(view_name)s (%(col_name)s);" % d)
            else:
                sql_stmts.append("CREATE UNIQUE INDEX %(vidx_name)s on %(view_name)s (%(col_name)s);" % d)
            sql_stmts.append("CREATE INDEX %(idx_name)s on %(table_name)s (%(col_name)s);" % d)


        # To synthesize unique_together over fields where NULLs are allowed,
        # we create a view per unique_together clause

        for fc_idx, field_constraints in enumerate(opts.unique_together):
            fields = [opts.get_field(f) for f in field_constraints]

            unique_together_fields = set([f for f in opts.local_fields if f.null]).intersection(set(fields))

            null_bits = ['%s IS NOT NULL' % style.SQL_FIELD(qn(f.column)) for f in fields if f.null]
            if len(null_bits) == 0:
                # No NULLable columns, skip this
                continue

            d ={'view_name': style.SQL_TABLE(qn("%s_%s_utvw" % (db_table, fc_idx))),
                'fields': ', \n    '.join([style.SQL_FIELD(qn(f.column)) for f in fields]),
                'table_name': style.SQL_TABLE(qn(db_table)),
                'null_parts': ' OR\n        '.join(null_bits),
                }

            sql_parts = []
            sql_parts.append("CREATE VIEW %(view_name)s WITH SCHEMABINDING " % d)
            sql_parts.append("    AS")
            sql_parts.append("    SELECT")
            sql_parts.append("    %(fields)s" % d)
            sql_parts.append("    FROM")
            sql_parts.append("        [dbo].%(table_name)s" % d)
            sql_parts.append("    WHERE")
            sql_parts.append("        %(null_parts)s" % d)
            sql_stmts.append('\n'.join(sql_parts))

            d ={'vidx_name' : style.SQL_TABLE(qn("%s_utidx_%s" % (db_table, fc_idx))),
                'view_name': style.SQL_TABLE(qn("%s_%s_utvw" % (db_table, fc_idx))),
                'table_name': style.SQL_TABLE(qn(db_table)),
                'col_names': ', '.join([style.SQL_FIELD(qn(f.column)) for f in fields]),
                }
            # Create a unique clustered index on the VIEW to enforce uniqueness
            # Note that the view itself will filter out the NULLable column 
            sql_stmts.append("CREATE UNIQUE CLUSTERED INDEX %(vidx_name)s on %(view_name)s (%(col_names)s);" % d)

            # Now, finally create a NON-unique index across the unique_together fields on the TABLE
            # to provide index speed
            d ={'idx_name' : style.SQL_TABLE(qn("%s_%s_ut_idx" % (db_table, fc_idx))),
                'table_name': style.SQL_TABLE(qn(db_table)),
                'col_name': ', '.join([style.SQL_FIELD(qn(f.column)) for f in fields]),
                }

            sql_stmts.append("CREATE INDEX %(idx_name)s on %(table_name)s (%(col_name)s);" % d)

            #sql_stmts.append("--  END SCHEMABINDING hack for %s" % style.SQL_TABLE(qn(db_table)))

            """
            Now for some closure magic.  We just grab the first field in the local_fields list
            and obtain the post_create_sql code, substituting in a lambda function if nothing
            is available.

            We apply a closure and extends the post_create_sql method with the SQL we've just 
            generated to synthesize proper UNIQUE+NULL capability
            """
            # We need to bind the sql_stmts to the first field 
            field = opts.local_fields[0]
            def wrap_statements(old_post_create_sql, stmts):
                def closure(style, db_table):
                    result = []
                    if old_post_create_sql:
                        result.extend([sql for sql in old_post_create_sql(style, db_table)])
                    result.extend(stmts)
                    return result
                return closure

            old_func = getattr(field, 'post_create_sql', lambda x, y : [])
            field.post_create_sql = wrap_statements(old_func, sql_stmts)

        return []

# Stored procedure code




