import os
import shutil
import tempfile
import zipfile
import glob
from optparse import make_option
from django.core.management.base import BaseCommand
from django.conf import settings
from django.template import Context, Template

# TODO: The (ab)use of __file__ makes me nervous. We should improve compatibility
#       with zipimport.

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--include-java-libs', dest='include_java_libs', default='',
                    help='List of java libraries (in the form of JAR files), '
                         'which must be included, separated by the "%s" '
                         'character. Typically used for JDBC drivers ' %
                         os.path.pathsep),
        make_option('--include-py-packages', dest='include_py_packages',
                    default='',
                    help='List of python top-level packages (directories) to '
                         'include separated by the "%s" character' %
                          os.path.pathsep),
        make_option('--include-py-path-entries', dest='include_py_path_entries',
                    default='',
                    help='List of python path entries (directories or JAR/ZIP '
                         'files) to include, separated by the "%s" character' %
                          os.path.pathsep),
        make_option('--context-root', dest='context_root', default='',
                    help='Name of the context root for the application. If '
                         'unspecified, the project name is used. The context '
                          'root name is used as the name of the WAR file, and '
                          'as a prefix for some url-related settings, such as '
                          'MEDIA_URL')
    )
    help = ("Builds a WAR file for stand-alone deployment on a Java "
            "Servlet container")

    def handle(self, *args, **options):
        project_name = self.project_name()
        context_root = options['context_root'] or project_name
        temp_dir = tempfile.mkdtemp()
        exploded_war_dir = os.path.join(temp_dir, project_name)
        print
        print "Assembling WAR on %s" % exploded_war_dir
        print
        self.copy_skel(exploded_war_dir)
        self.fill_templates(exploded_war_dir,
                            ['WEB-INF/web.xml', 'application.py'],
                            {'project_name': project_name,
                             'settings': settings})
        self.copy_jython(exploded_war_dir)
        self.copy_django(exploded_war_dir)
        self.copy_admin_media(exploded_war_dir)
        self.copy_project(exploded_war_dir)
        self.fix_project_settings(exploded_war_dir, context_root)
        self.copy_project_media(exploded_war_dir)
        self.copy_apps(exploded_war_dir)
        if options['include_java_libs']:
            for java_lib in options['include_java_libs'].split(os.path.pathsep):
                self.copy_java_jar(exploded_war_dir, java_lib)
        if options['include_py_packages']:
            py_package_dirs = options['include_py_packages'].split(
                os.path.pathsep)
            for py_package_dir in py_package_dirs:
                self.copy_py_package_dir(exploded_war_dir, py_package_dir)
        if options['include_py_path_entries']:
            py_path_entries = options['include_py_path_entries'].split(
                os.path.pathsep)
            for py_path_entry in py_path_entries:
                self.copy_py_path_entry(exploded_war_dir, py_path_entry)

        # I'm still unsure of wheter (by default) the WAR should be generated on
        # the parent directory of the project root or inside the generated
        # temporary directory.
        #
        # At least I'm sure I don't want to put it inside the project directory,
        # to avoid cluttering it, and to keep it simple the logic of copying the
        # project into the WAR (otherwise, it should special case the war file
        # itself)
        war_file_name = os.path.join(self.project_directory(),
                                     '..', context_root + '.war')
        self.war(exploded_war_dir, war_file_name)
        print "Cleaning %s..." % temp_dir
        shutil.rmtree(temp_dir)
        print """
Finished.

Now you can copy %s to whatever location your application server wants it.
""" % os.path.abspath(war_file_name)

    def copy_skel(self, exploded_war_dir):
        print "Copying WAR skeleton..."
        shutil.copytree(self._skel_directory(), exploded_war_dir)

    def _skel_directory(self):
        return os.path.join(os.path.dirname(__file__), 'war_skel')

    def fill_templates(self, exploded_war_dir, relative_file_names, vars):
        for relative_file_name in relative_file_names:
            file_name = os.path.join(*[exploded_war_dir] +
                                     relative_file_name.split('/'))
            template = Template(file(file_name).read())
            file(file_name, 'w').write(template.render(Context(vars)))

    def copy_jython(self, exploded_war_dir):
        jython_lib_path = os.path.dirname(os.path.abspath(os.__file__))
        jython_home = os.path.dirname(jython_lib_path)
        if jython_home.endswith('.jar'):
            # We are on a Jython stand-alone installation.
            self.copy_java_jar(exploded_war_dir, jython_home)
        else:
            # Is this Jython installation an official release version?
            if os.path.exists(os.path.join(jython_home, 'jython.jar')):
                self.copy_java_jar(exploded_war_dir,
                                   os.path.join(jython_home,
                                                'jython.jar'))
                # TODO: When jython2.5b2 goes out, find out if there is any
                #       extra step to include modjy.
                #
                #       Note that on the meantime, we aren't really supporting
                #       official releases of jython, as modjy wasn't being
                #       previously included.
            else:
                # SVN installation: jython-dev.jar inside jython_home. Also need
                # to include the extra java libraries
                self.copy_java_jar(exploded_war_dir,
                                   os.path.join(jython_home, 'jython-dev.jar'))
                for jar in glob.glob(os.path.join(jython_home,
                                                  'javalib', '*.jar')):
                    self.copy_java_jar(exploded_war_dir, jar)
                modjy_zip = glob.glob(os.path.join(jython_home,
                                                  'javalib', 'modjy*.zip'))[0]
                self.copy_modjy(exploded_war_dir, modjy_zip)
            self.copy_py_path_entry(exploded_war_dir, jython_lib_path)

    def copy_modjy(self, exploded_war_dir, modjy_zip_path):
        dest_name = os.path.basename(modjy_zip_path)
        print "Extracting modjy JAR from %s..." % dest_name
        modjy_release_name = dest_name[:-4]
        zip_file = zipfile.ZipFile(modjy_zip_path)
        jar_content = zip_file.read("%s/modjy_webapp/WEB-INF/lib/modjy.jar" %
                                    modjy_release_name)
        zip_file.close()
        dest_jar_path = os.path.join(exploded_war_dir, 'WEB-INF', 'lib',
                                     modjy_release_name + '.jar')
        dest_jar = file(dest_jar_path, 'wb')
        dest_jar.write(jar_content)
        dest_jar.close()


    def copy_django(self, exploded_war_dir):
        import django
        django_dir = os.path.dirname(os.path.abspath(django.__file__))
        self.copy_py_package_dir(exploded_war_dir, django_dir)

    def copy_admin_media(self, exploded_war_dir):
        from django.contrib import admin
        self.copy_media(exploded_war_dir,
                        os.path.join(os.path.dirname(admin.__file__), 'media'),
                        os.path.join(*settings.ADMIN_MEDIA_PREFIX.split('/')))

    def copy_project(self, exploded_war_dir):
        self.copy_py_package_dir(exploded_war_dir, self.project_directory())

    def fix_project_settings(self, exploded_war_dir, context_root):
        fix_media = (settings.MEDIA_URL and
                     not settings.MEDIA_URL.startswith('http'))
        fix_admin_media =  (settings.ADMIN_MEDIA_PREFIX and
                            not settings.ADMIN_MEDIA_PREFIX.startswith('http'))
        if not fix_media and not fix_admin_media:
            return

        fix = """
# Added by django-jython. Fixes URL prefixes to include the context root:
"""
        if fix_media:
            fix += "MEDIA_URL='/%s%s'\n" % (context_root, settings.MEDIA_URL)
        if fix_admin_media:
            fix += "ADMIN_MEDIA_PREFIX='/%s%s'\n" % (context_root,
                                                     settings.ADMIN_MEDIA_PREFIX)

        settings_name = settings.SETTINGS_MODULE.split('.')[-1]
        deployed_settings = os.path.join(exploded_war_dir,
                                         'WEB-INF',
                                         'lib-python',
                                         self.project_name(),
                                         settings_name + '.py')
        if os.path.exists(deployed_settings):
            settings_file_modified = file(deployed_settings, 'a')
            settings_file_modified.write(fix)
            settings_file_modified.close()
        else:
            print """WARNING: settings module file not found inside the project
directory (maybe you have split settings into a package?)

You SHOULD manually prefix the ADMIN_MEDIA_PREFIX and/or MEDIA_URL settings on the
deployed settings file. You can append the following block at the end of the file:

# ---------------------------- Begin Snip ---------------------------------
%s
# ----------------------------- End Snip -----------------------------------
""" % fix


    def copy_project_media(self, exploded_war_dir):
        if not settings.MEDIA_ROOT:
            print ("WARNING: Not copying project media, since MEDIA_ROOT "
                   "is not defined")
            return
        if not settings.MEDIA_URL:
            print ("WARNING: Not copying project media, since MEDIA_URL "
                   "is not defined")
            return
        if settings.MEDIA_URL.startswith('http'):
            print ("WARNING: Not copying project media, since MEDIA_URL "
                   "is absolute (starts with 'http')")
        self.copy_media(exploded_war_dir,
                        settings.MEDIA_ROOT,
                        os.path.join(*settings.MEDIA_URL.split('/')))

    def copy_apps(self, exploded_war_dir):
        for app in settings.INSTALLED_APPS:
            if app.startswith('django.') or \
                   app.startswith(self.project_name() + '.'):
                continue # Already included
            app_root_file = __import__(app).__file__
            app_root_dir = os.path.dirname(os.path.abspath(app_root_file))
            self.copy_py_package_dir(exploded_war_dir, app_root_dir)

    def copy_java_jar(self, exploded_war_dir, java_lib):
        # java_lib is a path to a JAR file
        dest_name = os.path.basename(java_lib)
        print "Copying %s..." % dest_name
        shutil.copy(java_lib,
                    os.path.join(exploded_war_dir,
                                 'WEB-INF', 'lib', dest_name))

    def copy_py_package_dir(self, exploded_war_dir, py_package_dir):
        """
        Copies a directory containing a python package to lib-python/
        """
        dest_name = os.path.basename(py_package_dir)
        print "Copying %s..." % dest_name
        shutil.copytree(py_package_dir,
                        os.path.join(exploded_war_dir,
                                     'WEB-INF', 'lib-python', dest_name))

    def copy_py_path_entry(self, exploded_war_dir, dir_or_file):
        """
        Copies a directory or zip/egg file to lib-python and generates a .pth
        file to make it part of sys.path
        """
        dest_name = os.path.basename(dir_or_file)
        print "Copying %s..." % dest_name
        dest_path = os.path.join(exploded_war_dir,
                                 'WEB-INF', 'lib-python', dest_name)
        shutil.copytree(dir_or_file, dest_path)
        pth_file = file(dest_path + '.pth', 'w')
        pth_file.write("%s\n" % dest_name)
        pth_file.close()

    def copy_media(self, exploded_war_dir, src_dir, dest_relative_path):
        if dest_relative_path[-1] == os.path.sep:
            dest_relative_path = dest_relative_path[:-1]
        if os.path.sep in dest_relative_path:
            # We have to construct the directory hierarchy (without the last
            # level)
            d = exploded_war_dir
            for sub_dir in os.path.split(dest_relative_path)[:-1]:
                d = os.path.join(d, sub_dir)
                os.mkdir(d)
        print "Copying %s..." % dest_relative_path
        shutil.copytree(src_dir,
                        os.path.join(exploded_war_dir, dest_relative_path))

    def war(self, exploded_war_dir, war_file_name):
        # Make sure we are working with absolute paths
        exploded_war_dir = os.path.abspath(exploded_war_dir)
        war_file_name = os.path.abspath(war_file_name)

        print "Building WAR on %s..." % war_file_name
        war = zipfile.ZipFile(war_file_name, 'w',
                              compression=zipfile.ZIP_DEFLATED)
        def walker(arg, directory, files):
            # The following "+ 1" accounts for the path separator after the
            # directory name
            relative_dir = directory[len(exploded_war_dir) + 1:]
            for f in files:
                file_name = os.path.join(directory, f)
                zip_file_name = os.path.join(relative_dir, f)
                if not os.path.isfile(file_name):
                    continue
                war.write(file_name,
                          os.path.join(relative_dir, f),
                          zipfile.ZIP_DEFLATED)
        os.path.walk(exploded_war_dir, walker, None)
        war.close()

    def settings_module(self):
        return __import__(settings.SETTINGS_MODULE, {}, {},
                          (settings.SETTINGS_MODULE.split(".")[-1],))
    def project_directory(self):
        return os.path.dirname(self.settings_module().__file__)

    def project_name(self):
        return os.path.basename(self.project_directory())

