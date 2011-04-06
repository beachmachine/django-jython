.. _war-deployment:

Creating a WAR Archive for Deployment
=====================================

django-jython includes a "war" management command so you can go to your project
directory and type something like this::

    lsoto@spirit:~/src/mysite$ jython manage.py war --include-java-libs=$HOME/jdbcdrivers/postgresql-8.3-603.jdbc4.jar

And get a single ``mysite.war`` file which you can deploy in your preferred application server. *This file doesn't require anything special installed on the target server*. No Django, no Jython, no nothing.

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

  $ jython manage.py war --include-java-libs=$HOME/jdbcdrivers/postgresql-8.3-603.jdbc4.jar

Here, you tell the war command that it should include an extra java library to
the generated WAR file, because it can't know which java libraries are you using
inside your project. In the typical cases, you must **at least** specify the
JDBC driver you are using to connect to the database, which will depend on the
configured :ref:`database-backends`

You may also specify more files to include, separating the paths by the special
**path separator** character, which is ``":"`` in Unix based platforms and
``";"`` on Windows platforms.

For example, if you are the iText library inside your Django project you should
specify something like the following when constructing the war file::

  $ jython manage.py war --include-java-libs=$HOME/jdbcdrivers/postgresql-8.3-603.jdbc4.jar:/usr/share/java/iText-2.1.3.jar 

By the way, *the generated WAR file is created on the parent directory of your
project directory*, in order to avoid cluttering your project space.

Including Extra files in WEB-INF/classes
----------------------------------------

As ``--include-java-libs`` adds Jar files to WEB-INF/lib of the generated war
file, you can use ``--include-in-classes`` to add other files to WEB_INF/classes. 
These will typically be resource files that your Java libraries load via a class 
loader. Entries will be directories separated using the **path separator** 
character as described in the previous section::

  $ jython manage.py war --include-in-classes=dir1:dir2 ...

Including Extra Python libraries
--------------------------------

By default, the war command copies your project directory and the root directory
of every django application declared on the ``INSTALLED_APPS`` settings inside
the generated file (in addition to django itself, of course). *It won't detect
any other python dependency of your project*, like for example PyAMF.

So, in case you have a dependency on a Python library (not included on the
standard library of course), you have to specify it with the
``--include-py-packages`` option, as the following example::

  $ jython manage.py war --include-java-libs=$HOME/jdbcdrivers/postgresql-8.3-603.jdbc4.jar --include-py-packages=$HOME/jython/Lib/site-packages/pyamf


Egg or zip files are also supported, as well as directories meant: to be "path
entries" (i.e, a directory _containing_ packages). For these cases, use the
``--include-py-path-entries`` option::

  $ jython manage.py war --include-java-libs=$HOME/jdbcdrivers/postgresql-8.3-603.jdbc4.jar --include-py-path-entries=$HOME/eggs/PyAMF-0.3.1-py2.5.egg

As with ``--include-java-libs``, multiple entries and/or packages can be
specified, by separating them with the **path separator** character of your
platform (``":"`` in Unix-based systems and ``";"`` in Windows).

All ``--include-*`` options  can be mixed freely.

Excluding Jython and Django
---------------------------

By default the ``war`` command will include a copy of Jython and Django
in the resulting war file.

.. note::

    Be aware that if you include Jython from a full (no standalone) installation, 
    the whole Jython directory tree will be copied to the war file, including
    ``site-packages``. Django-jython's ``war`` command takes care not to 
    duplicate in your war file packages that are installed in ``site-packages``,
    therefore if Django is already in ``site-packages`` it won't be added twice.

In some cases you may wish to reduce the size of the resulting .war file in
order to speed deployment and deploy multiple projects using a shared copy of
Jython, django-jython, and the Django libraries. In this case, you would use the
``--shared-war`` option with the war command::

   $ jython manage.py war --shared-war

This presupposes your JavaEE container is configured such that it can find
jython.jar, django-jython and the Django libraries. This may involve adding a
python.path property to your JVM settings, pointing it to the location of
django-jython and Django, and adding the Jython JAR file to the global CLASSPATH
of your JavaEE container. If you are using Glassfish, you need to add the JAR
file to the ``$DOMAINDIR/lib/ext`` directory or adding the location to the
``Libraries`` deployment option. If you are using Tomcat you would add the JAR
to ``$CATALINA_HOME/shared/lib``.

Media Files and the Context Root Name
-------------------------------------

In principle, your application could live "inside" any URL, as long as you use
the `url template tag
<http://www.djangoproject.com/documentation/templates/#url>`_ and the `reverse()
function <http://www.djangoproject.com/documentation/url_dispatch/#reverse>`_
to generate links inside your applications. This decouples your views from the
actual url they get "attached" to on the web server.

*But*, this isn't true for media files when the prefix is configured on
``settings.py``, such as ``MEDIA_URL`` and ``ADMIN_MEDIA_PREFIX``. (Now, if you
never planned to serve media on the same server where your django applications
live, skip this section. This is all about making it easy to serve static files
inside the **same** servlet context as your Django project will live.)

So, the war command patches the ``settings.py`` copied on the generated WAR, by
appending something like the following, at the end of the file::

  # Added by django-jython. Fixes URL prefixes to include the context root:
  MEDIA_URL='/mysite/site_media/'
  ADMIN_MEDIA_PREFIX='/mysite/media/'

(You can check this by yourself, looking at the file
``/WEB-INF/lib-python/<project_name>/settings.py`` inside the generated WAR
file)

This is done only if these variables are not blank (also, a warning is printed
when you build the WAR if any of them is blank) and don't seem to be a really
absolute URL (including the ``'http://'`` part), which mean that media files are
not going to live in the same server as the application.

By default, the war command assumes that you will use the name of the project as
the name of the context root in the deployed application. You can change this
using the ``--context-root=my_customized_context_root`` option of the command.

Please note that this small hack means that you can't simply rename your war
file to deploy it on another context name. You must regenerate it specifying the
other context name. Or just manually editing the settings.py file inside the
WAR, whatever fits you better.  

Sample Output
-------------

Currently the command is a bit verbose. As a reference, here is what I get when
running the command on the project you get after following the `official Django
tutorial <http://www.djangoproject.com/documentation/tutorial01/>`_ (up to
part three)::

  $ jython  manage.py war
  
  Assembling WAR on /var/folders/mQ/mQkMNKiaE583pWpee85FFk+++TI/-Tmp-/tmp4fkuU2/pollsite
  
  Copying WAR skeleton...
  Copying jython.jar...
  Copying Lib...
  Copying django...
  Copying media...
  Copying pollsite...
  WARNING: Not copying project media, since MEDIA_ROOT is not defined
  Copying doj...
  Building WAR on /Users/lsoto/src/jython-book/src/chapter14/tour/pollsite.war...
  Cleaning /var/folders/mQ/mQkMNKiaE583pWpee85FFk+++TI/-Tmp-/tmp4fkuU2...
  
  Finished.

  Now you can copy /Users/lsoto/src/jython-book/src/chapter14/tour/pollsite.war to whatever location your application server wants it.
