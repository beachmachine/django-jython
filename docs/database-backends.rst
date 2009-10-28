.. _database-backends:

Database Backends
=================

Backends are implemented using the great Jython's zxJDBC package, which makes
any database with a working JDBC driver accessible through the DB-API 2.0
specification. Thus, to use any backend from this project, you will also need
the corresponding JDBC driver somewhere in your ``CLASSPATH``. On Unix-based
environments this can be done on the console by running::

  $ export CLASSPATH="$CLASSPATH:/path/to/driver.jar"

Note that this is a ephemeral setting that will only have effect on the current
shell session.

PostgreSQL
----------

Very stable, and tested against PostgreSQL v8.3 with the JDBC driver
v8.3.603. To use it set the following in your Django project settings::

  DATABASE_ENGINE = 'doj.backends.zxjdbc.postgresql'

Download the JDBC Driver from http://jdbc.postgresql.org/download.html and
remember to put the JAR file on the ``CLASSPATH``.

Compatibility with the Django builtin PostgreSQL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In most cases, you can use the same database on Django applicatioons running on
CPython and Jython with the builtin `'postresql'` (or `'postgresql_psycopg2'`)
and this backend, respectively. **The only exception is for `IPAddressFields`**,
where the original backend uses a `inet` field while we use a `varchar`
one. This may change in the future, if/when the PostgreSQL JDBC driver make it
easy to deal with `inet` fields from Java.

SQLite3
-------

Experimental. By now, use it only if you are working on improving it. Or if you
are really adventurous.
