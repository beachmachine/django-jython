Release Notes
=============

1.3.0b1
-------

Released on April 1, 2011

Changes
~~~~~~~

No code changes.  Testing has been performed with Django 1.3 against the following
databases:

* PostgreSQL
* Oracle

1.2.0
-----

Released on April 1, 2011

Changes
~~~~~~~

None

1.2.0rc1
--------

Released on March 24, 2011.

Changes
~~~~~~~

Changes from the 1.2.0b1 release:

 - Repaired Issue #40: Query fails if unicode field in Oracle
 - Repaired Issue #39: Decimal in Oracle
 - Repaired Issue #38: Decimal support not working in MySQL backend

1.2.0b1
-------

Released on March 10, 2011.

Changes
~~~~~~~

Changes from the 1.1.1 release:

 - Oracle backend now compatible with Django 1.2.x
 - MySQL backend now compatible with Django 1.2.x
 - PostgreSQL backend now compatible with Django 1.2.x
 
Django Compatbility
~~~~~~~~~~~~~~~~~~~

This version has been tested against Django 1.2.3 and will work with any future
micro release of the 1.2.x branch.

Note that Django 1.0.x and 1.1.x are *NOT* supported by this release. If you need support
for Django 1.0.x or Django 1.1.0, please use previous releases of Django-Jython.

Jython compatibility
~~~~~~~~~~~~~~~~~~~~

The release has been tested on Jython 2.5.2 RC4. However, it should work on any
Jython 2.5.x release (including 2.5.0)

1.1.1
-----

Released on January 17, 2010.

Changes
~~~~~~~

Changes from the 1.1.0 release:

 - JNDI support added to all database backends, to leverage connection pools
   offered by Java application servers and servlet containers.
 - MySQL backend: Fixed problem with model inheritance with a concrete base. 
 - War deployment command: 

   - New ``--shared-war`` option to not bundle Django, Jython and django-jython
     in the WAR file, for enviroments in which those libraries are configured at
     the application server level and shared among all the web applications
     (thanks to John Sonnenschein for the contribution)
   - Fixed problem when ADMIN_MEDIA_PREFIX conflicts with MEDIA_URL but the
     admin app is not being used (issue 22)



Django Compatbility
~~~~~~~~~~~~~~~~~~~

This version has been tested against Django 1.1.1 and will work with any future
micro release of the 1.1.x branch.

Note that Django 1.0.x is *NOT* supported by this release. If you need support
for Django 1.0.x, use django-jython 1.0.

Jython compatibility
~~~~~~~~~~~~~~~~~~~~

The release has been tested on Jython 2.5.1. However, it should work on any
Jython 2.5.x release (including 2.5.0)

1.1.0
-----

Released on December 15, 2009.

Changes
~~~~~~~

Changes from the 1.0.0 release:

 - All database backends now work with Django 1.1.x
 - Django 1.0.x support removed

Django compatibility
~~~~~~~~~~~~~~~~~~~~

This version has been tested against Django 1.1.1 and will work with any future
micro release of the 1.1.x branch.

Note that Django 1.0.x is *NOT* supported by this release. If you need support
for Django 1.0.x, use django-jython 1.0.

Jython compatibility
~~~~~~~~~~~~~~~~~~~~

The release has been tested on Jython 2.5.1. However, it should work on any
Jython 2.5.x release (including 2.5.0)

1.0.0
-----

Released on November 8, 2009.

Changes
~~~~~~~

Changes from the 1.0.0b1 release:

 - Added Oracle backend
 - Added MySQL backend 
 - PostgreSQL backend: Works on Django 1.1.x
 - War command: Fixed problems when using multiple apps from a package not
   belonging to the project.
 - PostgreSQL backend: DecimalField works as expected
 - Added ``doj.VERSION`` following the same convention as ``django.VERSION``
 - Stand-alone documentation included on the distribution


Django Compatibility
~~~~~~~~~~~~~~~~~~~~

This version has been tested against Django 1.0.4. It may or may not work with
Django 1.1.1 (in particular, MySQL and Oracle database backends don't).

Users who get issues with currupted class files must apply the patch for `Django
bug #11621 <http://code.djangoproject.com/ticket/11621>`_.

Django 1.0.3 or earlier should not be used, since such releases have known
security vulnerabilities.

Jython Compatibility
~~~~~~~~~~~~~~~~~~~~

The release has been tested on Jython 2.5.1. However, it should work on any
Jython 2.5.x release (including 2.5.0)


1.0.0b1
-------

Released on April 20, 2009.

Changes
~~~~~~~

The following are the changes with respect to the original code (produced under
the GSoC 2008):

* modjy integration and war management command updated to work with Jython
  2.5b2 and later.
* Added ``doj.test.xmlrunner.junitxmlrunner``, a Django test runner for
  producing JUnit-compatible XML output (useful for integration with continous
  integration tools like hudson, cruise-control, etc).
* war command: ``--include-py-libs`` option has been renamed to
  ``--include-py-path-entries`` to avoid misinterpretations. Also added the
  ``--include-py-packages`` option.
* Bugfixes for all reported issues.

Django Compatibility
~~~~~~~~~~~~~~~~~~~~

This release is meant to be used with the current 1.0.X branch of Django. If for
some special reason you are stuck with 1.0.2, you should manually apply the
patch attached to `this issue <http://code.djangoproject.com/ticket/9789>`_

Once Django 1.0.3 is released, the subversion checkout won't be needed.

Please note that database backends included on this release of django-jython
will *not* work with Django 1.1.X.

Jython Compatibility
~~~~~~~~~~~~~~~~~~~~

This release is compatible with Jython 2.5b2 and later releases. 
