QuickStart
==========

Install
-------

To get started with using django-jython, first install it following these steps:

- Grab the `django-jython distribution <http://pypi.python.org/pypi/django-jython>`_
  suited for your Django version.
- Uncompress it
- Move into the resulting directory
- Run ``jython setup.py``

.. note::

   If you already have `pip <http://pypi.python.org/pypi/pip>`_ installed on
   Jython, you can use it instead of the manual process detailed above. The
   output looks like this::
   
     $ /path/to/jyton/bin/pip install django-jython
   
     Downloading/unpacking django-jython
       Downloading django-jython-1.7b2.tar.gz
       Running setup.py egg_info for package django-jython
     Installing collected packages: django-jython
       Running setup.py install for django-jython
     Successfully installed django-jython


Database backends
-----------------

Then, if you want to use the JDBC backends change the ``settings.py`` file of
your project and set::

  DATABASES = {
    'default': {
      # ...
      'ENGINE': 'doj.db.backends.postgresql',
    }
  }

Or::

  DATABASES = {
    'default': {
      # ...
      'ENGINE': 'doj.db.backends.sqlite',
    }
  }

Or::

  DATABASES = {
    'default': {
      # ...
      'ENGINE': 'doj.db.backends.mysql',
    }
  }

Or::

  DATABASES = {
    'default': {
      # ...
      'ENGINE': 'doj.db.backends.mssql',
    }
  }

Depending on which database you want to use. Remember to have the JAR file
containing the JDBC driver for each database somewhere in your
``CLASSPATH``. For example, you can do that on Unix-based system by running::

  export CLASSPATH="$CLASSPATH:/path/to/postgresql-9.1-902.jdbc4.jar"

For a complete documentation on building war files see :ref:`database-backends`.

Django and Jython
-----------------

The minimal required version of Jython to make Django work is 2.7.0. The required Django version
is 1.8.x.

Building a .war file
--------------------

To build a war archive for deployment into Java application servers, change
``settings.py`` on your project to include ``'doj'``. For example::

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

Then you can build a war file running ``jython manage.py buildwar`` on your project
directory.

For a complete documentation on building war files see :ref:`war-deployment`.
