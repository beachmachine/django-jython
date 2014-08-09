.. _war-deployment:

Creating a .war archive for deployment
======================================

django-jython includes a ``buildwar`` management command so you can go to your project
directory and type something like this::

    $ jython manage.py buildwar --include-java-libs=/path/to/jython-standalone-2.7-b2.jar:/path/to/postgresql-9.1-902.jdbc4.jar

And get a single ``mysite.war`` file which you can deploy in your preferred application server.
This file doesn't require anything special installed on the target server. No Django, no Jython, no nothing.

Usage
-----

The first step is to add ``'doj'`` to the list of ``INSTALLED_APPS`` on your
``settings.py`` file. So this section should look like::

  INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'mysite.polls',
    'mysite.another_app',
    # More apps...
    'doj',
  )

Then, the most typical usage is the one already exemplified::

  $ jython manage.py buildwar --include-java-libs=/path/to/jython-standalone-2.7-b2.jar:/path/to/postgresql-9.1-902.jdbc4.jar

Here, you tell the ``buildwar`` command that it should include an extra Java library to
the generated ``.war`` file, because it can't know which Java libraries are you using
inside your project. In the typical cases, you must **at least** specify the
JDBC driver you are using to connect to the database, which will depend on the
configured :ref:`database-backends`, as well as the **standalone version** of Jython itself.

The generated ``.war`` file is created on the current working directory.

You may also specify more files to include, separating the paths by the special
**path separator** character, which is ``:`` in Unix based platforms and
``;`` on Windows platforms.

For example, if you are using the iText library inside your Django project you should
specify something like the following when constructing the ``.war`` file::

  $ jython manage.py buildwar --include-java-libs=/path/to/jython-standalone-2.7-b2.jar:/path/to/postgresql-9.1-902.jdbc4.jar:/path/to/iText-2.1.3.jar

It is also possible to tell django-jython the needed Java library via the application's
settings. This has the advantage that there is no need to add the library paths to the
``buildwar`` command every time you build a new ``.war``. All you need to do is to add
a ``DOJ_BUILDWAR_JAVA_LIBS`` configuration to your settings::

  DOJ_BUILDWAR_JAVA_LIBS = [
    '/path/to/jython-standalone-2.7-b2.jar',
    '/path/to/postgresql-9.1-902.jdbc4.jar',
    '/path/to/iText-2.1.3.jar',
    # More .jars...
  ]

Including extra Python libraries
--------------------------------

By default, the ``buildwar`` command copies your project directory and the root directory
of every Django application declared on the ``INSTALLED_APPS`` settings inside
the generated file (in addition to Django itself, of course). **It won't detect
any other Python dependency of your project**, like for example PyAMF.

So, in case you have a dependency on a Python library (not included on the
standard library of course), you have to specify it with the
``--include-py-packages`` option, as the following example::

  $ jython manage.py buildwar --include-py-packages=pyamf

As with ``--include-java-libs``, multiple entries and/or packages can be
specified, by separating them with the **path separator** character of your
platform (``:`` in Unix-based systems and ``;`` in Windows).

Note that you do not add paths here, but Python module names. This means that
django-jython must be able to import the module with the given name (the package
must be in the Python path).

As with ``DOJ_BUILDWAR_JAVA_LIBS`` it is also possible to add the package
dependencies to your application's settings. This is done with the
``DOJ_BUILDWAR_PY_PACKAGES`` configuration::

  DOJ_BUILDWAR_PY_PACKAGES = [
    'pyamf',
    # More packages...
  ]

Media files and the context root name
-------------------------------------

In principle, your application could live inside any URL, as long as you use
the `url template tag
<http://www.djangoproject.com/documentation/templates/#url>`_ and the `reverse()
function <http://www.djangoproject.com/documentation/url_dispatch/#reverse>`_
to generate links inside your applications. This decouples your views from the
actual url they get attached to on the web server.

**But**, this isn't true for media files when the prefix is configured on
``settings.py``, such as ``MEDIA_URL`` or ``STATIC_URL``. (Now, if you
never planned to serve media on the same server where your Django applications
live, skip this section. This is all about making it easy to serve static files
inside the **same** servlet context as your Django project will live.)

So, the ``buildwar`` command patches the application's settings, by appending
something like the following, at the end of the file::

  # Added by django-jython. Fixes URL prefixes to include the context root:
  CONTEXT_ROOT='/mysite/'
  MEDIA_URL='/mysite/site_media/'
  STATIC_URL='/mysite/site_static/'
  LOGIN_REDIRECT_URL='/mysite/index/'
  LOGIN_URL='/mysite/login/'
  LOGOUT_URL='/mysite/logout/'

These values respect the original values of these variables. If any
of these variables do point to an remote server (e.g. starting with ``http://...``)
it will not get prefixed.

(You can check this by yourself, looking at the file
``WEB-INF/lib-python/application_settings.py`` inside the generated ``.war``
file)

By default, the ``buildwar`` command assumes that you will use the name of the project as
the name of the context root in the deployed application. You can change this
using the ``--context-root=my_customized_context_root`` option of the command.

You can also add the context root name to your application's settings by using the
``DOJ_BUILDWAR_CONTEXT_ROOT`` configuration::

  DOJ_BUILDWAR_CONTEXT_ROOT = 'my_customized_context_root'

Please note that this small hack means that you can't simply rename your war
file to deploy it on another context name. You must regenerate it specifying the
other context name. Or just manually editing the ``application_settings.py`` file
inside the ``.war``, whatever fits you better.
