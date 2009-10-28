JUnit XML Test Runner
=====================

On the Java world the JUnit XML output format is used by a lot of reporting
tools that make easier to browse test failures and compare them over the
time. Those are specially useful on continuous integration tools as `Hudson
<https://hudson.dev.java.net/>`_

Django-Jython includes a specialized test runner for the Django test framework
that will output the results of the test as an XML file compatible with
reporting tools expecting JUnit XML reports. 

To use it, put the following on your ``settings.py`` file::

  TEST_RUNNER='doj.test.xmlrunner.run_tests'

Then run the tests using the regular Django command::

  $ jython manage.py test

And then look for files named ``TEST-*.xml`` on the current directory.
