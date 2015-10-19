"""Module for managing/interacting with the local data store."""

import os
import glob
import sqlite3
from datetime import datetime


# Define some module constants
PATH_SQL = os.path.join(os.path.dirname(__file__), 'sql')
PATH_DAT_DEFAULT = os.path.join(os.getenv('HOME'), '.local', 'share',
                               'aa-chaos')
PATH_DAT = os.getenv('XDG_DATA_HOME', PATH_DAT_DEFAULT)
PATH_DB = os.path.join(PATH_DAT, 'store.db')


class DB(sqlite3.Connection):

    path_db = PATH_DB
    dtfmt = '%Y-%m-%d %H:%M'

    def __init__(self):
        # Connection is created on initialisation. If the database
        # file isn't present already, create the directory structure
        # and before initialising, then create the schema.
        fpath = self.path_db
        if not os.path.isfile(fpath):
            # mkdir -p
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            super().__init__(fpath)
            self.create()
        else:
            super().__init__(fpath)

    def __exit__(self, type, value, traceback):
        # sqlite3.Connection isn't closed on exit.
        self.commit()
        self.close()

    def create(self):
        """Create database schema."""
        # Fetch the CREATE TABLE statements from source and execute
        # them via the db connection.
        file_list = sorted(
            glob.glob(os.path.join(PATH_SQL, 'create*.sql')),
            key=lambda sql: 1 if 'vw' in sql else 0
        )

        for path in file_list:
            with open(path, 'r') as f:
                sql = f.read()
            self.execute(sql)
        self.commit()

    def insert_quota(self, pydt, remaining, total):
        """Store usage/quota at a given time."""
        self.execute("BEGIN TRANSACTION")
        try:
            self._insert_quota_history(pydt, remaining)
            self._insert_quota_monthly(pydt, total)
        except:
            self.execute("ROLLBACK")

    def _insert_quota_history(self, pydt, remaining):
        dbdt = self.pydt_to_dbdt(pydt)
        self.execute(
            """
            INSERT INTO quota_history
            VALUES (?, ?)
            """,
            (dbdt, remaining)
        )

    def _insert_quota_monthly(self, pydt, total):
        month_start = datetime(pydt.year, pydt.month, 1)
        dbdt = self.pydt_to_dbdt(month_start)
        self.execute(
            """
            INSERT INTO quota_monthly
            VALUES (?, ?)
            """,
            (dbdt, total)
        )

    # WIP
    #def dump(self, fpath):
    #    """Dump database contents to compressed, flat files."""
    #    # Alternative - http://codereview.stackexchange.com/q/78643
    #    for table in self.lstable():
    #        cur = self.conn.execute("SELECT * FROM {}".format(table))
    #        for record in cur.fetchall():
    #            fh.write(record)
    #    fh.close()

    def tables(self):
        """Return tuple of tables in the database."""
        cursor = self.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        )
        return tuple(
            table
            for tup in cursor.fetchall()
            for table in tup
        )

    @classmethod
    def pydt_to_dbdt(cls, pydt):
        """Convert a py datetime obj. to a SQLite-friendly string."""
        return pydt.strftime(cls.dtfmt)

    @classmethod
    def dbdt_to_pydt(cls, dbdt):
        """Convert a SQLite datetime string to a py datetime obj."""
        return datetime.strptime(dbdt, cls.dtfmt)
