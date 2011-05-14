from java.lang import Class
from java.lang import System
from java.io import PrintWriter
from java.sql import DriverManager
from java.sql import Connection
from java.sql import SQLException

#  Here are the dbcp-specific classes.
#  Note that they are only used in the setupDriver
#  method. In normal use, your classes interact
#  only with the standard JDBC API

from org.apache.commons.pool.impl import GenericObjectPool
from org.apache.commons.dbcp import PoolableConnectionFactory
from org.apache.commons.dbcp import BasicDataSource
from org.apache.commons.dbcp import DataSourceConnectionFactory
import time

class ManualPoolingDriver(object):
    def __init__(self, connectURI, username, password, pool_name):
        self.connectionPool = GenericObjectPool(None)
        self._pool_name = pool_name

        source = BasicDataSource()
        source.setUrl(connectURI)
        source.setUsername(username)
        source.setPassword(password)
        source.setInitialSize(1) # Number of connections to start with
        source.setMinIdle(5)     # Allow a bottom of 5 idle connections
        source.setMaxActive(10)  # Max of 10 database connection
        source.setDefaultTransactionIsolation(Connection.TRANSACTION_READ_COMMITTED)
        source.setMinEvictableIdleTimeMillis(500) 

        self.connectionFactory = DataSourceConnectionFactory(source)

        #  Now we'll create the PoolableConnectionFactory, which wraps
        #  the "real" Connections created by the ConnectionFactory with
        #  the classes that implement the pooling functionality.
        self.poolableConnectionFactory = PoolableConnectionFactory(self.connectionFactory,
                self.connectionPool,
                None,
                None,
                False,
                True)

        #  Finally, we create the PoolingDriver itself...
        Class.forName("org.apache.commons.dbcp.PoolingDriver")
        driver = DriverManager.getDriver("jdbc:apache:commons:dbcp:")

        #  ...and register our pool with it.
        driver.registerPool(self._pool_name, self.connectionPool)
        #  Now we can just use the connect string "jdbc:apache:commons:dbcp:<pool_name>"
        #  to access our pool of Connections.

    def printDriverStats(self):
        driver = DriverManager.getDriver("jdbc:apache:commons:dbcp:")
        connectionPool = driver.getConnectionPool(self._pool_name)
        print "NumActive: " + str(connectionPool.getNumActive())
        print "NumIdle: " + str(connectionPool.getNumIdle())

    def shutdownDriver(self):
        driver = DriverManager.getDriver("jdbc:apache:commons:dbcp:")
        driver.closePool(self._pool_name)

