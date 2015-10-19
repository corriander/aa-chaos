"""Module containing unit tests relating to local storage."""

import unittest
import os
import sqlite3
import tempfile
from datetime import datetime

from ddt import data, unpack, ddt as DDT
from store import DB

@DDT
class TestDB(unittest.TestCase):
    """Exercise the DB wrapper/adapter class.

    This test case contains a number of general methods for analysing
    a sqlite3 database, comparing schema to a known one, etc. This
    class depends on an easily configurable database path to avoid
    wiping out a "production" database, load reference dataset(s),
    etc.
    """

    path_refdb = os.path.join(
        os.path.dirname(__file__),
        'data',
        'test_store.db'
    )

    # TODO: Use mock for this!
    DB.path_db = path_refdb

    # ----------------------------------------------------------------
    # Class-level behaviour.
    # ----------------------------------------------------------------
    def test_context(self):
        """Test the context manager functionality."""
        stmt = "SELECT 'hello world'"

        with DB() as db:
            cursor = db.execute(stmt)
            result_set = cursor.fetchall()

        self.assertEqual(len(result_set), 1)
        self.assertRaises(
            sqlite3.ProgrammingError,
            cursor.execute,
            stmt
        )

    def test_expose_conn_attrs(self):
        """Check sqlite3 connection attributes/methods are exposed."""
        db = DB()
        db.execute("SELECT 'hello world'")

    # ----------------------------------------------------------------
    # Class component behaviour.
    # ----------------------------------------------------------------
    dt_examples = (
        ((2000, 1, 1, 18, 0), '2000-01-01 18:00'),
        ((2000, 1, 1), '2000-01-01 00:00')
    )

    @data(*dt_examples)
    @unpack
    def test_pydt_to_dbdt(self, pydt, dbdt):
        """Converts datetime object to SQLite TEXT object.

        This static method ensures datetime objects are stored
        correctly in the sqlite database. The format chosen is

        YYYY-MM-DD HH:MM
        """
        dt = datetime(*pydt)
        self.assertEqual(DB.pydt_to_dbdt(dt), dbdt)

    @data(*dt_examples)
    @unpack
    def test_dbdt_to_pydt(self, pydt, dbdt):
        """Converts SQLite TEXT datetime strings to py datetime.

        See test_pydt_to_dbdt.
        """
        dt = datetime(*pydt)
        self.assertEqual(DB.dbdt_to_pydt(dbdt), dt)

    def test_create(self):
        """Tests creation of a new database (schema).

        Method populates a fresh database.
        """
        # TODO: Use mock for this! If it fails, it borks other tests.
        DB.path_db = tempfile.mktemp()
        db = DB()
        tables = db.tables()
        self.assertEqual(len(tables), 2)
        self.assertCountEqual(
            tables,
            ('quota_history', 'quota_monthly')
        )

        os.remove(DB.path_db)
        DB.path_db = self.path_refdb

    def test_insert_quota(self):
        """Handles insertion of quota data.

        Quota takes a quota timestamp, remainder and total, and
        inserts this information into the quota_history and
        quota_monthly tables.
        """
        # FIXME: Failure of this test leaves rows in DB.
        # 98 GB left of 100 GB allowance on 2000-01-01T18:00
        quota = datetime(2001, 1, 1, 18), 98000000000, 100000000000
        with DB() as db:
            db.insert_quota(*quota)
            cursor = db.execute(
                """
                SELECT *
                FROM quota_vw
                WHERE
                    timestamp = (
                        SELECT timestamp
                        FROM quota_history
                        WHERE rowid = (
                            SELECT max(rowid)
                            FROM quota_history
                        )
                    )
                """
            )

            # Examine the selected record
            tstamp, rem, tot, pc = cursor.fetchone()

            self.assertEqual(
                datetime.strptime(tstamp, DB.dtfmt),
                quota[0]
            )
            self.assertListEqual([rem, tot], list(quota[1:]))

            # Tidy up the table.
            cursor.execute(
                """
                DELETE FROM quota_history
                WHERE rowid = (
                    SELECT max(rowid)
                    FROM quota_history
                )
                """
            )
            cursor.execute(
                """
                DELETE FROM quota_monthly
                WHERE rowid = (
                    SELECT max(rowid)
                    FROM quota_monthly
                )
                """
            )

    def test_tables(self):
        """Check that the list of tables in ref. db is as expected."""
        with DB() as db:
            tables = db.tables()

        self.assertEqual(len(tables), 3)
        # NOTE: assertItemsEqual replaces by assertCountEqual in Py3.2
        self.assertCountEqual(
            tables,
            ('quota_history', 'quota_monthly', 'test_table')
        )


if __name__ == '__main__':
    unittest.main()
