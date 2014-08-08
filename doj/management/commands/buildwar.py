# -*- coding: utf-8 -*-

import os
import tempfile
import zipfile

from optparse import make_option

from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.template import Context, Template

from doj.management.commands import DOJConfigurationMixin


class Command(NoArgsCommand, DOJConfigurationMixin):
    option_list = NoArgsCommand.option_list + (
        make_option('--include-java-libs', dest='include_java_libs', default='',
                    help=u"List of java libraries (in the form of JAR files), "
                         u"which must be included, separated by the \"%s\" "
                         u"character. Typically used for JDBC drivers " %
                         (os.path.pathsep, )),
        make_option('--include-py-packages', dest='include_py_packages',
                    default='',
                    help=u"List of python top-level packages (directories) to "
                         u"include separated by the \"%s\" character" %
                         (os.path.pathsep, )),
        make_option('--include-additional-dirs', dest='include_add_dirs',
                    default='',
                    help=u"List of Directories to put in WEB-INF Folder "
                         u"separated by the \"%s\" character" %
                         (os.path.pathsep, )),
        make_option('--project-name', dest='project_name', default='',
                    help=u"Name of the application used in description texts. If "
                         u"unspecified, the project name is generated from the "
                         u"application directory."),
        make_option('--project-description', dest='project_description', default='',
                    help=u"Description of the application used web.xml"),
        make_option('--context-root', dest='context_root', default='',
                    help=u"Name of the context root for the application. If "
                         u"unspecified, the project name is used. The context "
                         u"root name is used as the name of the .war file, and "
                         u"as a prefix for some url-related settings, such as "
                         u"MEDIA_URL"),
        make_option('--base-dir', dest='base_dir', default='',
                    help=u"The base directory of your project. If unspecified, "
                         u"the BASE_DIR configuration in your settings will be "
                         u"used."),
    )
    help = u"Builds a WAR file for stand-alone deployment on a Java Servlet container"
    requires_system_checks = True

    def __init__(self):
        super(Command, self).__init__()

        self._args = tuple()
        self._options = dict()

        self.__tmp_dir = None
        self.__base_dir = None

    def _get_skel_dir(self):
        return os.path.join(os.path.dirname(__file__), 'war_skel')

    def _get_temp_dir(self):
        """
        Creates a temporary directory where the content of the
        war will be generated.

        :return: Directory path
        """
        if not self.__tmp_dir:
            self.__tmp_dir = tempfile.mkdtemp(suffix='-buildwar')
        return self.__tmp_dir

    def _get_egg_list(self):
        egg_folder = os.path.join(self._get_temp_dir(), 'WEB-INF', 'lib-python')
        return [f for f in os.listdir(egg_folder) if os.path.isfile(os.path.join(egg_folder, f)) and f.endswith(('.egg', '.zip'))]

    def _is_media_included(self):
        """
        Determines if media files are included in the WAR. Media files are included
        when all of the following conditions are true:
        - `MEDIA_ROOT` is set and an existing directory
        - `MEDIA_URL` is set and an absolute, but not fully qualified, URL

        :return: Media included in WAR
        """
        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if not media_root:
            return False

        media_url = getattr(settings, 'MEDIA_URL', None)
        if not media_url or media_url[0] != '/':
            return False

        if not os.path.isdir(media_root):
            return False

        return True

    def _is_static_included(self):
        """
        Determines if static files are included in the WAR. Static files are included
        when all of the following conditions are true:
        - `STATIC_ROOT` is set and an existing directory
        - `STATIC_URL` is set and an absolute, but not fully qualified, URL

        :return: Static included in WAR
        """
        static_root = getattr(settings, 'STATIC_ROOT', None)
        if not static_root:
            return False

        static_url = getattr(settings, 'STATIC_URL', None)
        if not static_url or static_url[0] != '/':
            return False

        if not os.path.isdir(static_root):
            return False

        return True

    def handle_noargs(self, **options):
        self._setup(None, options)

        self.stdout.write(self.style.MIGRATE_LABEL(u"Assembling WAR"))
        self.stdout.flush()

        self.do_copy_skel()
        self.do_copy_media()
        self.do_copy_static()
        self.do_copy_apps()
        self.do_copy_py_packages()
        self.do_copy_java_libs()
        self.do_copy_additional_dirs()
        self.do_process_templates()
        self.do_build_war()

        self.stdout.write(self.style.MIGRATE_LABEL(u"Finished"))
        self.stdout.flush()

    def do_build_war(self):
        self.stdout.write(u"  Build %s.war..." % self._get_context_root(), ending='')
        self.stdout.flush()

        temp_path = self._get_temp_dir()
        war_path = os.path.abspath("%s.war" % self._get_context_root())

        war_file = zipfile.ZipFile(war_path, 'w', compression=zipfile.ZIP_DEFLATED)

        def war_walker(arg, directory, files):
            # The following "+ 1" accounts for the path separator after the
            # directory name
            relative_dir = directory[len(temp_path) + 1:]
            for f in files:
                src_file_path = os.path.join(directory, f)
                zip_file_path = os.path.join(relative_dir, f)

                if not os.path.isfile(src_file_path):
                    continue

                war_file.write(src_file_path, zip_file_path, zipfile.ZIP_DEFLATED)

        os.path.walk(temp_path, war_walker, None)
        war_file.close()
        rmtree(temp_path)

        self.stdout.write(self.style.MIGRATE_SUCCESS(u" OK"))
        self.stdout.flush()

    def do_copy_skel(self):
        self.stdout.write(u"  Copy skeleton...", ending='')
        self.stdout.flush()

        copytree(self._get_skel_dir(), self._get_temp_dir())

        self.stdout.write(self.style.MIGRATE_SUCCESS(u" OK"))
        self.stdout.flush()

    def do_copy_media(self):
        self.stdout.write(u"  Copy media...", ending='')
        self.stdout.flush()

        if not self._is_media_included():
            self.stdout.write(self.style.ERROR(u" SKIP"))
            self.stdout.flush()
            return

        media_path = settings.MEDIA_ROOT
        media_url = settings.MEDIA_URL
        copytree(media_path, os.path.join(self._get_temp_dir(), media_url))

        self.stdout.write(self.style.MIGRATE_SUCCESS(u" OK"))
        self.stdout.flush()

    def do_copy_static(self):
        self.stdout.write(u"  Copy static...", ending='')
        self.stdout.flush()

        if not self._is_static_included():
            self.stdout.write(self.style.ERROR(u" SKIP"))
            self.stdout.flush()
            return

        static_path = settings.STATIC_ROOT
        static_url = settings.STATIC_URL
        copytree(static_path, os.path.join(self._get_temp_dir(), static_url))

        self.stdout.write(self.style.MIGRATE_SUCCESS(u" OK"))
        self.stdout.flush()

    def do_copy_apps(self):
        self.stdout.write(u"  Copy apps...", ending='')
        self.stdout.flush()

        app_pkgs = list()

        for app in self._get_django_apps():
            app_pkg = app.split('.')[0]
            if app_pkg not in app_pkgs:
                app_pkgs.append(app_pkg)

        for app_pkg in app_pkgs:
            module = __import__(app_pkg)
            app_path = os.path.dirname(module.__file__)
            app_target = os.path.join(self._get_temp_dir(), 'WEB-INF', 'lib-python', app_pkg)
            copytree(app_path, app_target, False, ignore_in_sources)

        self.stdout.write(self.style.MIGRATE_SUCCESS(u" OK"))
        self.stdout.flush()

    def do_copy_additional_dirs(self):
        self.stdout.write(u"  Copy additional directories...", ending='')
        self.stdout.flush()

        for src_path in self._get_additional_dirs():
            if not os.path.isdir(src_path):
                continue

            dst_path = os.path.join(self._get_temp_dir(), os.path.basename(src_path))
            copytree(src_path, dst_path)

        self.stdout.write(self.style.MIGRATE_SUCCESS(u" OK"))
        self.stdout.flush()

    def do_copy_java_libs(self):
        self.stdout.write(u"  Copy java libraries...", ending='')
        self.stdout.flush()

        for lib in self._get_java_libs():
            if not os.path.isfile(lib):
                continue

            lib_name = os.path.basename(lib)
            lib_target = os.path.join(self._get_temp_dir(), 'WEB-INF', 'lib', lib_name)
            copy(lib, lib_target)

        self.stdout.write(self.style.MIGRATE_SUCCESS(u" OK"))
        self.stdout.flush()

    def do_copy_py_packages(self):
        self.stdout.write(u"  Copy python packages...", ending='')
        self.stdout.flush()

        pkgs = list()

        for pkg in self._get_python_packages():
            pkg = pkg.split('.')[0]
            if pkg not in pkgs:
                pkgs.append(pkg)

        for pkg in pkgs:
            module = __import__(pkg)

            if os.path.basename(module.__file__).startswith(('__init__.', '__init__$')):  # multi file package
                pkg_path = os.path.dirname(module.__file__)

                if os.path.isdir(pkg_path):  # package is a folder
                    pkg_target = os.path.join(self._get_temp_dir(), 'WEB-INF', 'lib-python', pkg)
                    copytree(pkg_path, pkg_target, False, ignore_in_sources)
                elif os.path.isfile(os.path.dirname(pkg_path)):  # package is a zipped egg
                    pkg_path = os.path.dirname(pkg_path)
                    egg_name = os.path.basename(pkg_path)
                    pkg_target = os.path.join(self._get_temp_dir(), 'WEB-INF', 'lib-python', egg_name)
                    copy(pkg_path, pkg_target)
            else:  # single file module
                pkg_path = module.__file__
                pkg_target = os.path.join(self._get_temp_dir(), 'WEB-INF', 'lib-python', os.path.basename(module.__file__))
                copy(pkg_path, pkg_target)

        self.stdout.write(self.style.MIGRATE_SUCCESS(u" OK"))
        self.stdout.flush()

    def do_process_templates(self):
        self.stdout.write(u"  Process skeleton templates...", ending='')
        self.stdout.flush()

        temp_dir = self._get_temp_dir()
        templates = [
            'wsgi.py.tmpl',
            'WEB-INF/web.xml.tmpl',
            'WEB-INF/lib-python/application_settings.py.tmpl',
            'WEB-INF/lib-python/eggs.pth.tmpl',
        ]
        context = Context({
            'project_name': self._get_project_name(),
            'project_description': self._get_project_description(),
            'context_root': self._get_context_root(),
            'is_media_included': self._is_media_included(),
            'is_static_included': self._is_static_included(),
            'egg_list': self._get_egg_list(),
            'settings': settings,
        })

        for template in templates:
            template_path = os.path.join(temp_dir, template)
            target_path = template_path.rsplit('.', 1)[0]

            template_file = file(template_path, 'r')
            target_file = file(target_path, 'w')

            template = Template(template_file.read())
            target_file.write(template.render(context))

            template_file.close()
            target_file.close()

            os.remove(template_path)

        self.stdout.write(self.style.MIGRATE_SUCCESS(u" OK"))
        self.stdout.flush()


def rmtree(target_dir):
    """
    Removes the given directory.

    :param dir: Directory path
    """
    import shutil

    if os.path.isdir(target_dir):
        shutil.rmtree(target_dir)


def copytree(src, dst, symlinks=False, ignore=None):
    """
    Copies a directory from source to destination path. This function
    works similar to `shutil.copytree`, but does not break if
    destination directory is already existing.

    :param src: Source path
    :param dst: Destination path
    :param symlinks: Copy symlinks as symlinks
    :param ignore: Ignore callback
    """
    import shutil

    if os.path.exists(dst):
        shutil.rmtree(dst)

    shutil.copytree(src, dst, symlinks, ignore)


def copy(src, dst):
    """
    Copies a file from source to destination.

    :param src: Source file
    :param dst: Destination file
    """
    import shutil

    if not os.path.exists(dst) or os.stat(src).st_mtime - os.stat(dst).st_mtime > 1:
        shutil.copy2(src, dst)


def ignore_in_sources(d, files):
    """
    Ignore callback for `copytree` to exclude files you usually not want to
    be in the application sources on production systems.

    :param d: Directory path
    :param files: Files in that directory
    :return: List of ignored files
    """
    ignored_prefixes = ('.', '~')
    ignored_suffixes = ('$py.class', '.pyc', '.pyo', '.war', '.jar')
    ignored_folders = tuple()

    if getattr(settings, 'MEDIA_ROOT', None):
        ignored_folders += (settings.MEDIA_ROOT.rstrip('/\\'), )

    if getattr(settings, 'STATIC_ROOT', None):
        ignored_folders += (settings.STATIC_ROOT.rstrip('/\\'), )

    if d.startswith(ignored_folders):
        return files
    return [f for f in files if f.startswith(ignored_prefixes) or f.endswith(ignored_suffixes)]