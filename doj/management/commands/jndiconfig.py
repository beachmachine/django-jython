# -*- coding: utf-8 -*-

import os

from optparse import make_option

from django.db import connection
from django.core.management.base import NoArgsCommand, CommandError
from django.template import Context, Template

from doj.management.commands import DOJConfigurationMixin


class Command(NoArgsCommand, DOJConfigurationMixin):
    option_list = NoArgsCommand.option_list + (
        make_option('--project-name', dest='project_name', default='',
                    help=u"Name of the application used in description texts. If "
                         u"unspecified, the project name is generated from the "
                         u"application directory."),
        make_option('--context-root', dest='context_root', default='',
                    help=u"Name of the context root for the application. If "
                         u"unspecified, the project name is used. The context "
                         u"root name is used as the name of the configuration "
                         u"file."),
        make_option('--base-dir', dest='base_dir', default='',
                    help=u"The base directory of your project. If unspecified, "
                         u"the BASE_DIR configuration in your settings will be "
                         u"used."),
    )
    help = u"Prints the JNDI datasource configuration for the default database"
    requires_system_checks = True

    def __init__(self):
        super(Command, self).__init__()

        self._args = tuple()
        self._options = dict()

        self.__database_configuration = None

    def _get_database_configuration(self):
        if not self.__database_configuration:
            self.__database_configuration = dict(connection.settings_dict)
        return self.__database_configuration

    def _get_skel_dir(self):
        return os.path.join(os.path.dirname(__file__), 'jndi_skel')

    def _get_resource_name(self):
        """
        Gets the resource name for the JNDI configuration from the
        ``JNDI_NAME`` entry in the database ``OPTIONS``

        :return: Resource name
        """
        settings_dict = self._get_database_configuration()
        jndi_name = settings_dict.get('OPTIONS', {}).get('JNDI_NAME', '')
        return jndi_name.replace('java:comp/env/', '')

    def _is_jndi_enabled(self):
        """
        Checks if a JNDI configuration can be created for the
        current database configuration. The configuration can be created if
        all of the following conditions are true:
        - The connection has a ``get_jdbc_driver_class_name`` method
        - The connection has a ``get_jdbc_connection_url`` method
        - The ``JNDI_NAME`` entry is set on the database ``OPTIONS``

        :return: JNDI configuration possible
        """
        settings_dict = self._get_database_configuration()

        if not hasattr(connection, 'get_jdbc_driver_class_name'):
            return False
        if not hasattr(connection, 'get_jdbc_connection_url'):
            return False
        if not 'OPTIONS' in settings_dict:
            return False
        if not 'JNDI_NAME' in settings_dict['OPTIONS']:
            return False
        return True

    def handle_noargs(self, **options):
        self._setup(None, options)

        self.do_print_configuration()

        self.stdout.write(u"")
        self.stdout.write(self.style.MIGRATE_LABEL(u"Usage hint:"))
        self.stdout.write(
            u"For a basic configuration of JNDI on your Tomcat server, "
            u"create a file named %s.xml on "
            u"'/path/to/apache-tomcat-6.x.x/conf/Catalina/localhost/' with "
            u"the content printed above." % (self._get_context_root(), )
        )

    def do_print_configuration(self):
        if not self._is_jndi_enabled():
            raise CommandError(u"Cannot create JNDI configuration for your database configuration. "
                               u"Make sure you are using a django-jython database backend, and "
                               u"your database configuration has a 'JNDI_NAME' in it's 'OPTIONS'.")

        settings_dict = self._get_database_configuration()
        skel_dir = self._get_skel_dir()
        context = Context({
            'project_name': self._get_project_name(),
            'resource_name': self._get_resource_name(),
            'username': settings_dict.get('USER', ''),
            'password': settings_dict.get('PASSWORD', ''),
            'driver_class': connection.get_jdbc_driver_class_name(),
            'connection_url': connection.get_jdbc_connection_url(),
        })

        template_path = os.path.join(skel_dir, 'jndidatasource.xml.tmpl')
        template_file = file(template_path, 'r')

        template = Template(template_file.read())
        self.stdout.write(template.render(context))

        template_file.close()