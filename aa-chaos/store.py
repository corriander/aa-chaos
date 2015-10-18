"""Module for managing/interacting with the local data store."""

import os
import glob
import sqlite3


# Define some module constants
PATH_SQL = os.path.join(os.path.dirname(__file__), 'sql')
PATH_DAT_DEFAULT = os.path.join(os.getenv('HOME'), '.local', 'share',
                               'aa-chaos')
PATH_DAT = os.getenv('XDG_DATA_HOME', PATH_DAT_DEFAULT)
PATH_DB = os.path.join(PATH_DAT, 'store.db')


class DB(object):

    def __init__(self):
        self._conn = self.connect(PATH_DB)

    @property
    def conn(self):
        """Current, active SQLite3 API connection object."""
        return self._conn

    def connect(self, fpath):
        """Return connection object for the database at fpath."""

        # Check the database is actually present.
        if not os.path.isfile(fpath):
            conn = self.create(fpath)
        else:
            conn = sqlite3.connect(fpath)

        return conn

    def create(self, fpath):
        """Create database and return connection."""
        os.makedirs(os.path.dirname(fpath), exist_ok=True) # mkdir -p
        conn = sqlite3.connect(fpath) # Implicitly creates a DB file.

        # Fetch the CREATE TABLE statements from source and execute
        # them via the db connection.
        for match in glob.glob(os.path.join(PATH_SQL, 'create*.sql')):
            with open(match, 'r') as f:
                sql = f.read()
            conn.execute(sql)
            conn.commit()

        return conn

    # WIP
    #def dump(self, fpath):
    #    """Dump database contents to compressed, flat files."""
    #    # Alternative - http://codereview.stackexchange.com/q/78643
    #    for table in self.lstable():
    #        cur = self.conn.execute("SELECT * FROM {}".format(table))
    #        for record in cur.fetchall():
    #            fh.write(record)
    #    fh.close()

    def lstable(self):
        """List tables in the database."""
        cursor = self.conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        )
        return cursor.fetchall()
