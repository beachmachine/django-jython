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

Oracle
------

The Oracle database backend is fairly stable and has been tested extensively.
The Oracle backend has been tested with Oracle version 10.2.0.3, 10.2.0.4, and
11.1.0.6.  To use it set the following in your Django project settings::

  DATABASE_ENGINE = 'doj.backends.zxjdbc.oracle'

Oracle has several different JDBC drivers, however only ojdbc14.jar has been
extensively tested.  The next target for testing is ojdbc6.jar for use with
11.1.0.7 database.  You can obtain a copy of the Oracle JDBC drivers from the
Oracle site at http://www.oracle.com/technology/software/tech/java/sqlj_jdbc/index.html.
Remember to put the JAR file on the ``CLASSPATH``.

MySQL
------

The MySQL database backend has been exposed to limited practical testing, but
appears mostly stable.  It has been tested with MySQL version 5.1.34-community
on Windows XP SP3. To use it set the following in your Django project settings::

  DATABASE_ENGINE = 'doj.backends.zxjdbc.mysql'

MySQL has several different JDBC drivers, however only mysql-connector-java-5.1.10-bin.jar has been extensively tested.

Remember to put the JAR file on the ``CLASSPATH``.

Known issues are that FilePathField does not require you to set the path
attribute, and URLField is not able to verify that a server returned a 404
error.
