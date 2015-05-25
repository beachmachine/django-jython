.. _database-backends:

Database backends
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

Developed and tested against PostgreSQL v9.3 with the JDBC driver
9.4-1201.jdbc41. To use it set the following in your Django project settings::

  DATABASES = {
    'default': {
      # ...
      'ENGINE': 'doj.db.backends.postgresql',
    }
  }

Download the JDBC Driver from http://jdbc.postgresql.org/download.html and
remember to put the JAR file on the ``CLASSPATH``.

SQLite3
-------

Developed and tested against SQLite3 v3.7.6 with the JDBC driver
3.8.10. To use it set the following in your Django project settings::

  DATABASES = {
    'default': {
      # ...
      'ENGINE': 'doj.db.backends.sqlite',
    }
  }

Download the JDBC Driver from https://bitbucket.org/xerial/sqlite-jdbc/downloads and
remember to put the JAR file on the ``CLASSPATH``.

MySQL/MariaDB
-------------

Developed and tested against MariaDB 10.0.17 with the JDBC driver
5.1.35. To use it set the following in your Django project settings::

  DATABASES = {
    'default': {
      # ...
      'ENGINE': 'doj.db.backends.mysql',
    }
  }

Download the JDBC Driver from http://dev.mysql.com/downloads/connector/j and
remember to put the JAR file on the ``CLASSPATH``.

MSSQL
-----

Developed and tested against MSSQL 2008 with the JDBC driver
1.3.1. To use it set the following in your Django project settings::

  DATABASES = {
    'default': {
      # ...
      'ENGINE': 'doj.db.backends.mssql',
    }
  }

Download the JDBC Driver from http://jtds.sourceforge.net/ and
remember to put the JAR file on the ``CLASSPATH``.

JNDI support
------------

All the backends documented on the previous sections support JNDI lookups to
leverage connection pools provided by Java application servers. To use JNDI,
simply add the following line to the project's ``settings.py``::

  DATABASES = {
    'default': {
      # ...
      'OPTIONS': {
        'JNDI_NAME': 'java:comp/env/jdbc/myDataSource',
      }
    }
  }

And make sure that the datasource specified as the ``JNDI_NAME`` is defined on
the application server in which you will deploy your application.

.. note::

  When using JNDI and with the exception of ``ENGINE``, all the other
  options will be ignored by django-jython. For ease of
  development you may want to add the ``JNDI_NAME`` option **only** to the staging
  and production servers. After all, on most cases you won't really need
  database connection pooling when testing on your development machine.

Specifying additional JNDI options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Additionally, you can use the ``'JNDI_CONTEXT_OPTIONS'`` entry of the
``OPTIONS`` dictionary to pass `additional options
<http://java.sun.com/j2se/1.5.0/docs/api/javax/naming/Context.html#INITIAL_CONTEXT_FACTORY>`_
to set up the underlying JNDI ``InitialContext``. The options are themselves
specified as another dictionary. For example::

  DATABASES = {
    'default': {
      # ...
      'OPTIONS': {
        'JNDI_NAME': 'java:comp/env/jdbc/myDataSource',
        'JNDI_CONTEXT_OPTIONS': {
          'java.naming.factory.initial': 'com.sun.appserv.naming.S1ASCtxFactory',
          'com.sun.appserv.iiop.endpoints': 'localhost:3700',
        }
      }
    }
  }

Note that usually you don't need to pass additional options for JNDI to work if
the application has been deployed on a JavaEE container (such as Tomcat,
Glassfish, JBoss, Websphere, Weblogic, etc). We provide this setting for
flexibility and completeness. But on most cases the configuration will look like
the one-liner shown on the first JNDI settings example.

JNDI and Tomcat
~~~~~~~~~~~~~~~

To use django-jython JNDI support on top of Apache Tomcat, add the JNDI
configuration line to your settings.py::
  
  DATABASES = {
    'default': {
      # ...
      'OPTIONS': {
        'JNDI_NAME': 'java:comp/env/jdbc/myDataSource'
      }
    }
  }

Do **not** remove the other database settings, as they will be used by
django-jython to help you create your JNDI configuration.

Deploy your application as normal. It won't work (raising a JNDI exception
telling you that *the jdbc name is not bound in this Context*), but we will fix
that now. Use the ``jndiconfig`` management command to get a sample context XML
file to set up your data source::

  $ jython manage.py jndiconfig

You will see an output similar to this::

  <!-- This is the JNDI datasource configuration for mysite -->
  <Context>
    <!-- Some documentation... -->
    <Resource name="jdbc/myDataSource"
              auth="Container"
              type="javax.sql.DataSource"
              username="root"
              password="root"
              driverClassName="com.mysql.jdbc.Driver"
              url="jdbc:mysql://localhost:3306/mydatabase?zeroDateTimeBehavior=convertToNull"
              maxActive="8"
              maxIdle="4"
              maxWait="10000"/>
  </Context>

  Usage hint:
    For a basic configuration of JNDI on your Tomcat server, create a file named mysite.xml on
    '/path/to/apache-tomcat-6.x.x/conf/Catalina/localhost/' with the content printed above.

Follow the instructions, restart Tomcat and it will be working as expected.
