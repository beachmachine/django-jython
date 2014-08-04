# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import sys
import time
import django

from unittest import expectedFailure

from django.conf import settings
from django.db import connections
from django.utils import six
from django.utils.module_loading import import_string

from doj.db.backends import JDBCBaseDatabaseCreation as BaseDatabaseCreation


class DatabaseCreation(BaseDatabaseCreation):
    # This dictionary maps Field objects to their associated Server Server column
    # types, as strings. Column-type strings can contain format strings; they'll
    # be interpolated against the values of Field.__dict__.
    data_types = {
        'AutoField':                    'int IDENTITY (1, 1)',
        'BigAutoField':                 'bigint IDENTITY (1, 1)',
        'BigIntegerField':              'bigint',
        'BinaryField':                  'varbinary(max)',
        'BooleanField':                 'bit',
        'CharField':                    'nvarchar(%(max_length)s)',
        'CommaSeparatedIntegerField':   'nvarchar(%(max_length)s)',
        'DateField':                    'date',
        'DateTimeField':                'datetime2',
        'DateTimeOffsetField':          'datetimeoffset',
        'DecimalField':                 'decimal(%(max_digits)s, %(decimal_places)s)',
        'FileField':                    'nvarchar(%(max_length)s)',
        'FilePathField':                'nvarchar(%(max_length)s)',
        'FloatField':                   'double precision',
        'GenericIPAddressField':        'nvarchar(39)',
        'IntegerField':                 'int',
        'IPAddressField':               'nvarchar(15)',
        'NullBooleanField':             'bit',
        'OneToOneField':                'int',
        'PositiveIntegerField':         'int',
        'PositiveSmallIntegerField':    'smallint',
        'SlugField':                    'nvarchar(%(max_length)s)',
        'SmallIntegerField':            'smallint',
        'TextField':                    'nvarchar(max)',
        'TimeField':                    'time',
    }

    # Starting with Django 1.7, check constraints are no longer included in with
    # the data_types value.
    data_type_check_constraints = {
        'PositiveIntegerField': '%(qn_column)s >= 0',
        'PositiveSmallIntegerField': '%(qn_column)s >= 0',
    }

    def __init__(self, *args, **kwargs):
        super(DatabaseCreation, self).__init__(*args, **kwargs)

    def mark_tests_as_expected_failure(self, failing_tests):
        """
        Flag tests as expectedFailure. This should only run during the
        testsuite.
        """
        django_version = django.VERSION[:2]
        for test_name, versions in six.iteritems(failing_tests):
            if not versions or not isinstance(versions, (list, tuple)):
                # skip None, empty, or invalid
                continue
            if not isinstance(versions[0], (list, tuple)):
                # Ensure list of versions
                versions = [versions]
            if all(map(lambda v: v[:2] != django_version, versions)):
                continue
            test_case_name, _, method_name = test_name.rpartition('.')
            test_case = import_string(test_case_name)
            method = getattr(test_case, method_name)
            method = expectedFailure(method)
            setattr(test_case, method_name, method)

    def create_test_db(self, *args, **kwargs):
        #self.mark_tests_as_expected_failure(self.connection.features.failing_tests)
        super(DatabaseCreation, self).create_test_db(*args, **kwargs)

    def _create_test_db(self, verbosity=1, autoclobber=False):
        """
        Create the test databases using a connection to database 'master'.
        """
        if self._test_database_create(settings):
            try:
                with self.connection.cursor():
                    test_database_name = super(DatabaseCreation, self)._create_test_db(verbosity, autoclobber)
            except Exception as e:
                if 'Choose a different database name.' in str(e):
                    six.print_('Database "%s" could not be created because it already exists.' % test_database_name)
                else:
                    six.reraise(*sys.exc_info())
            self.install_regex_clr(test_database_name)
            return test_database_name

        if verbosity >= 1:
            six.print_("Skipping Test DB creation")
        return self._get_test_db_name()

    def _destroy_test_db(self, test_database_name, verbosity=1):
        """
        Drop the test databases using a connection to database 'master'.
        """
        if not self._test_database_create(settings):
            if verbosity >= 1:
                six.print_("Skipping Test DB destruction")
            return

        for alias in connections:
            connections[alias].close()
        try:
            with self.connection.cursor() as cursor:
                qn_db_name = self.connection.ops.quote_name(test_database_name)
                # boot all other connections to the database, leaving only this connection
                cursor.execute("ALTER DATABASE %s SET SINGLE_USER WITH ROLLBACK IMMEDIATE" % qn_db_name)
                time.sleep(1)
                # after we switch to master, database is clear to drop
                cursor.execute("USE [master]")
                cursor.execute("DROP DATABASE %s" % qn_db_name)
        except Exception:
            six.reraise(*sys.exc_info())

    def _test_database_create(self, settings):
        """
        Check the settings to see if the test database should be created.
        """
        if 'TEST_CREATE' in self.connection.settings_dict:
            return self.connection.settings_dict.get('TEST_CREATE', True)
        if hasattr(settings, 'TEST_DATABASE_CREATE'):
            return settings.TEST_DATABASE_CREATE
        else:
            return True

    def install_regex_clr(self, database_name):
        sql = '''
USE {database_name};

-- Enable CLR in this database
sp_configure 'show advanced options', 1;
RECONFIGURE;
sp_configure 'clr enabled', 1;
RECONFIGURE;

-- Drop and recreate the function if it already exists
IF OBJECT_ID('REGEXP_LIKE') IS NOT NULL
    DROP FUNCTION [dbo].[REGEXP_LIKE]

IF EXISTS(select * from sys.assemblies where name like 'regex_clr')
    DROP ASSEMBLY regex_clr
;

CREATE ASSEMBLY regex_clr
FROM 0x{assembly_hex}
WITH PERMISSION_SET = SAFE;

create function [dbo].[REGEXP_LIKE]
(
    @input nvarchar(max),
    @pattern nvarchar(max),
    @caseSensitive int
)
RETURNS INT  AS
EXTERNAL NAME regex_clr.UserDefinedFunctions.REGEXP_LIKE
        '''.format(
            database_name=self.connection.ops.quote_name(database_name),
            assembly_hex=self.get_regex_clr_assembly_hex(),
        ).split(';')

        with self.connection.cursor() as cursor:
            for s in sql:
                cursor.execute(s)

    def get_regex_clr_assembly_hex(self):
        import os
        import binascii
        with open(os.path.join(os.path.dirname(__file__), 'regex_clr.dll'), 'rb') as f:
            assembly = binascii.hexlify(f.read()).decode('ascii')
        return assembly