# -*- coding: utf-8 -*-

import os

from django.conf import settings


class DOJConfigurationMixin(object):
    def _setup(self, args, options):
        """
        Makes the given arguments an options available
        to all methods.

        :param args: Command arguments as tuple
        :param options: Command arguments as dict
        """
        self._args = args or tuple()
        self._options = options or dict()

    def _get_base_dir(self):
        """
        Gets the path to the project base.

        :return: Directory path
        """
        if not self.__base_dir:
            self.__base_dir = self._options.get('base_dir', None)
            if not self.__base_dir:
                self.__base_dir = getattr(settings, 'BASE_DIR', None)

            if not self.__base_dir:
                self.__base_dir = os.path.dirname(settings.__file__)

        return self.__base_dir

    def _get_project_name(self):
        """
        Gets a descriptive name of the project.

        :return: Name
        """
        project_name = self._options['project_name']
        if not project_name:
            project_name = getattr(settings, 'DOJ_BUILDWAR_PROJECT_NAME', None)
            if not project_name:
                project_name = os.path.basename(self._get_base_dir())

        return project_name

    def _get_project_description(self):
        """
        Gets a description for the project.

        :return: Name
        """
        project_description = self._options['project_description']
        if not project_description:
            project_description = getattr(settings, 'DOJ_BUILDWAR_PROJECT_DESCRIPTION', None)
            if not project_description:
                project_description = self._get_project_name()

        return project_description

    def _get_context_root(self):
        """
        Gets the context name of the project.

        :return: Context name
        """
        context_root = self._options['context_root']
        if not context_root:
            context_root = getattr(settings, 'DOJ_BUILDWAR_CONTEXT_ROOT', None)
            if not context_root:
                context_root = self._get_project_name()

        return context_root.strip().replace(' ', '_')

    def _get_django_apps(self):
        """
        Gets a list of installed Django apps.

        :return: List of app names
        """
        return list(getattr(settings, 'INSTALLED_APPS', list()))

    def _get_python_packages(self):
        """
        Gets a list of python packages that should be included in the WAR. First the
        method looks for the `--include-py-packages` option, then for
        `DOJ_BUILDWAR_PY_PACKAGES` in the settings.

        :return: List of package names
        """
        packages = [p for p in self._options['include_py_packages'].split(os.path.pathsep) if p]
        if not packages:
            packages = getattr(settings, 'DOJ_BUILDWAR_PY_PACKAGES', list())

        return [package.strip() for package in packages]

    def _get_java_libs(self):
        """
        Gets a list of java libraries that should be included in the WAR. First the
        method looks for the `--include-java-libs` option, then for
        `DOJ_BUILDWAR_JAVA_LIBS` in the settings.

        :return: List of absolute paths to .jar files
        """
        libs = [l for l in self._options['include_java_libs'].split(os.path.pathsep) if l]
        if not libs:
            libs = getattr(settings, 'DOJ_BUILDWAR_JAVA_LIBS', list())
        return [l.strip() for l in libs]

    def _get_additional_dirs(self):
        """
        Gets a list of additional directories that should be included in the WAR.
        First the method looks for the `--include-additional-dirs` option, then for
        `DOJ_BUILDWAR_ADDITIONAL_DIRS` in the settings.

        :return: List of absolute paths to additional directories
        """
        dirs = [d for d in self._options['include_add_dirs'].split(os.path.pathsep) if d]
        if not dirs:
            dirs = getattr(settings, 'DOJ_BUILDWAR_ADDITIONAL_DIRS', list())
        return [d.strip() for d in dirs]