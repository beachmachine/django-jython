from pprint import pprint
try:
    # Force the database driver to load 
    from java.lang import Class
    cls = Class.forName("net.sourceforge.jtds.jdbc.Driver").newInstance()
    from jtds.mssql2k.pool import ManualPoolingDriver
    from com.ziclix.python.sql import zxJDBC as Database
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading zxJDBC module: %s" % e)

db_dict = {
        'DATABASE_NAME': 'test_zxjdbc.jtds',
        'DATABASE_HOST': 'localhost',
        'DATABASE_PORT': 1433,
        }
pool_name = 'jdbc_pool'
print "Registering driver for : %s to [%s]" % (str(db_dict), pool_name)
driver = ManualPoolingDriver("jdbc:jtds:sqlserver://%(DATABASE_HOST)s:%(DATABASE_PORT)s/%(DATABASE_NAME)s" % db_dict, 
                            'sa',
                            'sa',
                            pool_name,
                            )


from java.sql import DriverManager
from java.sql import Types
url='jdbc:apache:commons:dbcp:%s' % pool_name
conn = DriverManager.getConnection(url)
proc = conn.prepareCall("returnpage(?, ?, ?, ?)");
proc.setString('@query', "select * from foo_simple");
proc.setString('@orderby', "auto asc");
proc.setInt('@startrow', 5);
proc.setInt('@endrow', 12);
proc.execute()

rset = proc.getResultSet()
meta = rset.getMetaData()



type_dict = {}
for key in dir(Types):
    type_dict[getattr(Types, key)]=key

pprint (type_dict)

getter = {1: rset.getString,
 2: rset.getLong,
 3: rset.getBigDecimal,
 4: rset.getInt,
 5: rset.getInt,
 6: rset.getFloat,
 7: rset.getFloat,
 8: rset.getDouble,
 12: rset.getString,
 16: rset.getBoolean,
 70: rset.getString,
 91: rset.getDate,
 92: rset.getTime,
 93: rset.getTimestamp,
 }

col_count = meta.getColumnCount()
col_getter = {}

for i in range(1, col_count+1):
    col_getter[i] = getter[meta.getColumnType(i)]

while rset.next():
    for colnum in range(1, col_count+1):
        value = col_getter[colnum](colnum)
        print type(value), value,"|",
    print 
    print '-' * 20

