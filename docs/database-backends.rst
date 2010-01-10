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

JNDI Support
------------

All the backends documented on the previous sections support JNDI lookups to
leverage connection pools provided by Java application servers. To use JNDI,
simply add the following line to the project's ``settings.py``::

  DATABASE_OPTIONS = {'JNDI_NAME': 'java:comp/env/jdbc/myDataSource'}

And make sure that the datasource specified as the ``JNDI_NAME`` is defined on
the application server in which you will deploy your application.

.. note::

  When using JNDI and with the exception of ``DATABASE_BACKEND``, all the other
  ``DATABASE_*`` options will be ignored by django-jython. For ease of
  development you may want to add the ``JNDI_NAME`` option *only* to the staging
  and production servers. After all, on most cases you won't really need
  database connection pooling when testing on your development machine.

Specifying additional JNDI options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Additionally, you can use the ``'JNDI_CONTEXT_OPTIONS'`` entry of the
``DATABASE_OPTIONS`` dictionary to pass ``additional options
<http://java.sun.com/j2se/1.5.0/docs/api/javax/naming/Context.html#INITIAL_CONTEXT_FACTORY>``_
to set up the underlying JNDI ``InitialContext``. The options are themselves
specified as another dictionary. For example::

  DATABASE_OPTIONS = {
    'JNDI_NAME': 'java:comp/env/jdbc/your-datasource',
    'JNDI_CONTEXT_OPTIONS': {
      'java.naming.factory.initial': 'com.sun.appserv.naming.S1ASCtxFactory',
      'com.sun.appserv.iiop.endpoints': 'localhost:3700'
    }
  }

Note that usually you don't need to pass additional options for JNDI to work if
the application has been deployed on a JavaEE container (such as Tomcat,
Glassfish, JBoss, Websphere, Weblogic, etc). We provide this setting for
flexibility and completeness. But on most cases the configuration will looklike
the one-liner shown on the first JNDI settings example.

Recipe: JNDI and Tomcat
~~~~~~~~~~~~~~~~~~~~~~~

To use django-jython JNDI support on top of Apache Tomcat, add the JNDI
configuration line to your settings.py::
  
  DATABASE_OPTIONS = {'JNDI_NAME': 'java:comp/env/jdbc/myDataSource'}

Do *not* remove the other ``DATABASE_*`` settings, as they will be used by
django-jython to help you create your JNDI configuration.

Deploy your application as normal. It won't work (raising a JNDI exception
telling you that "the jdbc name is not bound in this Context"), but we will fix
that now. Use the tomcat management command to get a sample context XML file to
set up your data source::

  $ jython manage.py tomcat jndiconfig

You will see an output similar to this::

  For a basic configuration of JNDI on your Tomcat server, create a file named
  pollsite.xml on /path/to/apache-tomcat-6.x.x/conf/Catalina/localhost/ with the
  following contents:
  
  <Context>
    <Resource name="jdbc/myDataSource"
              auth="Container"
              type="javax.sql.DataSource"
              username="lsoto"
              password="secret"
              driverClassName="org.postgresql.Driver"
              url="jdbc:postgresql://localhost/pollsite"
              maxActive="8"
              maxIdle="4"/>
  </Context>
  
  Do NOT forget to copy the JDBC Driver jar file to the lib/ directory of your 
  Tomcat instalation

Follow the instructions, restart Tomcat and it will be working as expected.
