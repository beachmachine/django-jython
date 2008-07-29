from django.db.backends.postgresql.creation import DATA_TYPES as PG_DATA_TYPES
import copy

DATA_TYPES = copy.copy(PG_DATA_TYPES)

# Avoid using the inet data type, because using it from JDBC is a pain.
#
# By reading http://archives.postgresql.org/pgsql-jdbc/2007-08/msg00089.php
# seems like we would have to patch the JDBC driver with this extension:
# http://oak.cats.ohiou.edu/~rf358197/jdbc/2/.
DATA_TYPES['IPAddressField'] = 'char(15)'

