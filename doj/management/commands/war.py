import os
import shutil
import tempfile
from optparse import make_option
from django.core.management.base import BaseCommand
from django.conf import settings

# TODO: The (ab)use of __file__ makes me nervous. Check compatibility with
#       zipimport.
#
#       Also, I'd like to move application.py out of the WAR root. Need to check
#       if modjy can support a path relative to the war root to specify the
#       location of application.py.

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--include-java-libs', dest='include_java_libs', default='',
            help='Comma separated list of java libraries (JAR files) to '
                 'include. Typically used for JDBC drivers '),
        make_option('--include-py-libs', dest='include_py_libs', default='',
            help='Comma separated list of python libraries (directories '
                  'or JAR/ZIP files) to include')
    )
    help = ("Builds a WAR file for stand-alone deployment on a Java "
            "Servlet container")
    def handle(self, *args, **options):
        project_name = self.project_name()
        exploded_war_dir = os.path.join(tempfile.mkdtemp(), project_name)
        print
        print "Assembling WAR on %s" % exploded_war_dir
        self.copy_skel(exploded_war_dir)
        self.fill_templates(exploded_war_dir,
                            ['WEB-INF/web.xml', 'application.py'],
                            {'project_name': project_name,
                             'settings_module': settings.SETTINGS_MODULE})
        self.copy_jython(exploded_war_dir)
        self.copy_django(exploded_war_dir)
        self.copy_project(exploded_war_dir)
        self.copy_apps(exploded_war_dir)
        if options['include_java_libs']:
            for java_lib in options['include_java_libs'].split(','):
                self.copy_java_lib(exploded_war_dir, java_lib)
        if options['include_py_libs']:
            for py_lib in options['inclide_py_libs'].split(','):
                self.copy_py_lib(exploded_war_dir, py_lib)
        print "Finished."

    def copy_skel(self, exploded_war_dir):
        print "Copying WAR skeleton..."
        shutil.copytree(self._skel_directory(), exploded_war_dir)

    def _skel_directory(self):
        return os.path.join(os.path.dirname(__file__), 'war_skel')

    def fill_templates(self, exploded_war_dir, relative_file_names, vars):
        for relative_file_name in relative_file_names:
            file_name = os.path.join(*[exploded_war_dir] +
                                     relative_file_name.split('/'))
            content = file(file_name).read()
            file(file_name, 'w').write(content % vars)

    def copy_jython(self, exploded_war_dir):
        print "Copying Jython core..."
        jython_lib_path = os.path.dirname(os.path.abspath(os.__file__))
        jython_home = os.path.dirname(jython_lib_path)
        if jython_home.endswith('.jar'):
            # We are on a Jython stand-alone installation.
            self.copy_java_lib(exploded_war_dir, jython_home)
        else:
            # Standard installation: jython.jar inside jython_home
            self.copy_java_lib(exploded_war_dir,
                               os.path.join(jython_home, 'jython.jar'))
            # XXX: Right now (August 2008), on the asm branch in subversion,
            # jython.jar depends on a javalib/jarjar.jar file, containing the
            # runtime dependencies. In the future this step may not be needed
            self.copy_java_lib(exploded_war_dir,
                               os.path.join(jython_home, 'javalib', 'jarjar.jar'))
            self.copy_py_lib(exploded_war_dir, jython_lib_path)


    def copy_django(self, exploded_war_dir):
        import django
        django_dir = os.path.dirname(os.path.abspath(django.__file__))
        self.copy_py_lib(exploded_war_dir, django_dir)


    def copy_project(self, exploded_war_dir):
        self.copy_py_lib(exploded_war_dir, self.project_directory())

    def copy_apps(self, exploded_war_dir):
        for app in settings.INSTALLED_APPS:
            if app.startswith('django.') or \
                   app.startswith(self.project_name() + '.'):
                continue # Already included
            app_first_dir = os.path.dirname(os.path.abspath(__import__(app).__file__))
            self.copy_py_lib(exploded_war_dir, app_first_dir)

    def copy_java_lib(self, exploded_war_dir, java_lib):
        # java_lib is a path to a JAR file
        dest_name = os.path.basename(java_lib)
        print "Copying %s..." % dest_name
        shutil.copy(java_lib,
                    os.path.join(exploded_war_dir,
                                 'WEB-INF', 'lib', dest_name))

    def copy_py_lib(self, exploded_war_dir, py_lib_dir):
        dest_name = os.path.basename(py_lib_dir)
        print "Copying %s..." % dest_name
        if dest_name != 'Lib':
            # Each python library goes into its own sys.path entry (Except Lib,
            # which is itself a sys.path entry. Maybe I should add some flag to
            # this method instead of special-casing Lib)
            os.mkdir(os.path.join(exploded_war_dir,
                                  'WEB-INF', 'lib-python', dest_name))
            dest_name = os.path.join(dest_name, dest_name)

        shutil.copytree(py_lib_dir,
                        os.path.join(exploded_war_dir,
                                     'WEB-INF', 'lib-python', dest_name))

    def settings_module(self):
        return __import__(settings.SETTINGS_MODULE, {}, {},
                          (settings.SETTINGS_MODULE.split(".")[-1],))
    def project_directory(self):
        return os.path.dirname(self.settings_module().__file__)

    def project_name(self):
        return os.path.basename(self.project_directory())

