import sys
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
        make_option('--include-in-classes', dest='include_in_classes',
                    default='',
                    help='List of directories with files that must be '
                         'included in WEB-INF/classes, separated by the "%s" character. '
                         'Use this option to include additional resources '
                         'required by your aplication.' %
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
                          'MEDIA_URL'),
        make_option('--shared-war', action='store_true', dest='shared_war',
                    help='Do not include Jython, it\'s libraries, django-jython,'
                         'or Django. Useful for deployment of multiple django '
                         'projects on a single app server. Note that your '
                         'application server must be configured to correctly '
                         'find jython.jar, django-jython, and the Jython and '
                         'Django libs. '),
        make_option('--keep-temp-files', action='store_true', dest='keep_temp_files',
                    help='Do not delete the temporary files with the exploded '
                         'war file. You can use this feature for debugging '
                         'purposes.'),
    )
    help = ("Builds a WAR file for stand-alone deployment on a Java "
            "Servlet container")

    def handle(self, *args, **options):
        project_name = self.project_name()
        context_root = options['context_root'] or project_name
        temp_dir = tempfile.mkdtemp()
        exploded_war_dir = os.path.join(temp_dir, project_name)
        if ('django.contrib.admin' in settings.INSTALLED_APPS) and \
                (settings.ADMIN_MEDIA_PREFIX == settings.MEDIA_URL):
            print
            print "Both ADMIN_MEDIA_PREFIX and MEDIA_URL point to %s" % settings.MEDIA_URL
            print "This will cause admin media files to override project media files"
            print "Please change your settings and run the war command again"
            print
            sys.exit(1)
        print "Assembling WAR on %s" % exploded_war_dir
        print
        self.copy_skel(exploded_war_dir)
        self.fill_templates(exploded_war_dir,
                            ['WEB-INF/web.xml', 'application.py'],
                            {'project_name': project_name,
                             'settings': settings})
        if not options['shared_war']:
            self.copy_jython(exploded_war_dir)
            self.copy_django(exploded_war_dir)
        self.copy_project(exploded_war_dir)
        self.fix_project_settings(exploded_war_dir, context_root)
        self.copy_project_media(exploded_war_dir)
        self.copy_admin_media(exploded_war_dir)
        if not options['shared_war']:
            self.copy_apps(exploded_war_dir, settings.INSTALLED_APPS)
        else:
            self.copy_apps(exploded_war_dir, 
                           [app for app in settings.INSTALLED_APPS if app != "doj"])
        if options['include_java_libs']:
            for java_lib in options['include_java_libs'].split(os.path.pathsep):
                self.copy_java_jar(exploded_war_dir, java_lib)
        if options['include_in_classes']:
            include_in_classes = options['include_in_classes'].split(
                os.path.pathsep)
            for data_dir in include_in_classes:
                self.copy_to_classes(exploded_war_dir, data_dir)
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
        if not options['keep_temp_files']:
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
            f = file(file_name, 'w')
            f.write(template.render(Context(vars)))
            f.close()

    def get_jython_home(self):
        jython_lib_path = os.path.dirname(os.path.abspath(os.__file__))
        return os.path.dirname(jython_lib_path), jython_lib_path

    def copy_jython(self, exploded_war_dir):
        jython_home, jython_lib_path = self.get_jython_home()
        if jython_home.endswith('.jar'):
            # We are on a Jython stand-alone installation.
            self.copy_java_jar(exploded_war_dir, jython_home)
        else:
            # Is this Jython installation an official release version?
            if os.path.exists(os.path.join(jython_home, 'jython.jar')):
                self.copy_java_jar(exploded_war_dir,
                                   os.path.join(jython_home,
                                                'jython.jar'))
            else:
                # SVN installation: jython-dev.jar inside jython_home. Also need
                # to include the extra java libraries
                self.copy_java_jar(exploded_war_dir,
                                   os.path.join(jython_home, 'jython-dev.jar'))
                for jar in glob.glob(os.path.join(jython_home,
                                                  'javalib', '*.jar')):
                    self.copy_java_jar(exploded_war_dir, jar)
            self.copy_py_path_entry(exploded_war_dir, jython_lib_path)
            # create_site_packages_pth():
            site_packages_pth = os.path.join(exploded_war_dir,
                                    'WEB-INF', 'lib-python', 'site-packages.pth')
            pth_file = file(site_packages_pth, 'w')
            libdir_name = os.path.basename(jython_lib_path)
            site_packages_rel_path = os.path.join(libdir_name, 'site-packages')
            pth_file.write("%s\n" % site_packages_rel_path)
            for egg in glob.glob(os.path.join(jython_lib_path, 'site-packages', '*.egg')):
                pth_file.write("%s\n" % os.path.join(site_packages_rel_path, os.path.basename(egg)))
            pth_file.close()

    def copy_django(self, exploded_war_dir):
        import django
        django_dir = os.path.dirname(os.path.abspath(django.__file__))
        jython_home, jython_lib_path = self.get_jython_home()
        if not django_dir.startswith(jython_lib_path):
            self.copy_py_package_dir(exploded_war_dir, django_dir)

    def copy_admin_media(self, exploded_war_dir):
        if 'django.contrib.admin' not in settings.INSTALLED_APPS:
            print "Skipping admin media: django.contrib.admin not in INSTALLED_APPS"
            return
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

    def copy_apps(self, exploded_war_dir, apps):
        already_included_pkgs = ['django', self.project_name()]
        for app in apps:
            # We copy the whole package in which the app resides
            app_pkg = __import__(app)
            if app_pkg.__name__ in already_included_pkgs:
                continue
            app_pkg_dir = os.path.dirname(os.path.abspath(app_pkg.__file__))
            jython_home, jython_lib_path = self.get_jython_home()
            if not app_pkg_dir.startswith(jython_lib_path):
                self.copy_py_package_dir(exploded_war_dir, app_pkg_dir)
            already_included_pkgs.append(app_pkg.__name__)

    def copy_java_jar(self, exploded_war_dir, java_lib):
        # java_lib is a path to a JAR file
        dest_name = os.path.basename(java_lib)
        print "Copying %s..." % dest_name
        shutil.copy(java_lib,
                    os.path.join(exploded_war_dir,
                                 'WEB-INF', 'lib', dest_name))

    def copy_to_classes(self, exploded_war_dir, data_dir):
        """
        Copies files from a directory to classes/
        """
        print "Copying files from %s to WEB-INF/classes..." % data_dir
        shutil.copytree(data_dir,
                        os.path.join(exploded_war_dir,
                                     'WEB-INF', 'classes'))

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
                if not os.path.exists(d):
                    os.mkdir(d)
        print "Copying %s..." % dest_relative_path
        shutil.copytree(src_dir,
                        os.path.join(exploded_war_dir, dest_relative_path))
        # check if media src_dir is within project folder, then remove
        # duplicates from war
        project_dir = self.project_directory()
        jython_home, jython_lib_path = self.get_jython_home()
        dupe_root = None
        if src_dir.startswith(project_dir):
            dupe_root = project_dir
            dest_dir = self.project_name()
        elif src_dir.startswith(jython_lib_path):
            dupe_root = jython_lib_path             
            dest_dir = os.path.basename(jython_lib_path)            
        if dupe_root:
            # get the relative path of original media in packed war and remove
            src_rel_dir = src_dir[len(dupe_root) + 1:]
            print(" - source: %s" % src_dir)
            duplicate_media = os.path.join(exploded_war_dir, "WEB-INF", 
                "lib-python", dest_dir, src_rel_dir)
            print("Removing duplicate media: %s" % duplicate_media)
            shutil.rmtree(os.path.join(duplicate_media))

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

