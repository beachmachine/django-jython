Release Notes
=============

1.0.0
-----

Released on ???

Changes
~~~~~~~~

With respect to the 1.0.0b1 release:

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
