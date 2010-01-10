from django.core.management.base import BaseCommand
from django.conf import settings
import os

class Command(BaseCommand):
    subcommands = {
        "jndiconfig": "Prints a sample context XML configuration with the "
                       "appropriate JNDI datasource configuration for "
                       "connection pooling"
    }
    subcommands_help = "\n\n".join("%s\n    %s" % (subcmd, subhelp)
                                   for subcmd, subhelp in subcommands.items())
    help = ("Utilities for deployment and configuration on tomcat\n\n"
            "Subcommands:\n\n" + subcommands_help)

    def handle(self, *args, **options):
        if not args:
            print "You need to pass one subcommand as argument"
            print "Available subcommands:\n"
            print self.subcommands_help
            return
        if args[0] not in self.subcommands.keys():
            print "Subcommand %s not recognized\n" % args[0]
            print self.subcommands_help
            return
        getattr(self, args[0])(args, options)
    
    def jndiconfig(self, *args, **options):
        def usage():
            print
            print "Add a line to your settings.py specifying the name of your JNDI datasource such as DATABASE_OPTIONS = {'JNDI_NAME': 'java:comp/env/jdbc/myDataSource'} and keep the other DATABASE settings untouched"
        def resource_name():
            return settings.DATABASE_OPTIONS['JNDI_NAME'].replace('java:comp/env/', '')
        if not hasattr(settings, 'DATABASE_OPTIONS'):
            print "You haven't set the DATABASE_OPTIONS"
            usage()
            return
        if not 'JNDI_NAME' in settings.DATABASE_OPTIONS:
            print "You haven't set the JNDI_NAME entry on DATABASE_OPTIONS"
            usage()
            return
        from django.db import connection
        print ("\nFor a basic configuration of JNDI on your Tomcat server, "
               "create a file named %s.xml on "
               "/path/to/apache-tomcat-6.x.x/conf/Catalina/localhost/ "
               "with the following contents:" % self.project_name())
        print """
<Context>
  <Resource name="%s"
            auth="Container"
            type="javax.sql.DataSource"
            username="%s"
            password="%s"
            driverClassName="%s"
            url="%s"
            maxActive="8"
            maxIdle="4"/>
</Context>
""" % (resource_name(), settings.DATABASE_USER, 
       settings.DATABASE_PASSWORD, connection.driver_class_name, 
       connection.jdbc_url())
        print ("Do NOT forget to copy the JDBC Driver jar file to the lib/ "
               "directory of your Tomcat instalation")

    def project_directory(self):
        return os.path.dirname(self.settings_module().__file__)

    def project_name(self):
        return os.path.basename(self.project_directory())

    def settings_module(self):
        return __import__(settings.SETTINGS_MODULE, {}, {},
                          (settings.SETTINGS_MODULE.split(".")[-1],))

