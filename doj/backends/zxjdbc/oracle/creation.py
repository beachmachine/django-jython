import copy
from django.db.backends.creation import BaseDatabaseCreation
from django.db.backends.oracle.creation import DatabaseCreation as OracleDatabaseCreation

class DatabaseCreation(BaseDatabaseCreation):
    def __init__(self, *args, **kwargs):
        super(DatabaseCreation, self).__init__(*args, **kwargs)
        # Avoid using the inet data type, because using it from JDBC is a pain.
        #
        # By reading http://archives.postgresql.org/pgsql-jdbc/2007-08/msg00089.php
        # seems like we would have to patch the JDBC driver with this extension:
        # http://oak.cats.ohiou.edu/~rf358197/jdbc/2/.
        self.data_types = copy.copy(OracleDatabaseCreation.data_types)
        self.data_types['IPAddressField'] = 'char(15)'
