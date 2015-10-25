"""Module containing unit tests relating to local storage."""

import unittest
import os
import sqlite3
import tempfile
from datetime import datetime
from collections import namedtuple

from ddt import data, unpack, ddt as DDT

from aachaos.store import DB


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
    # TODO: Move to memory?
    DB.path_db = path_refdb

    def setUp(self):
        # Create a connection to the reference database.
        self.db = DB()

    def tearDown(self):
        # Undo changes to the database made in the test.
        self.db.rollback()

    # ----------------------------------------------------------------
    # Class-level behaviour.
    # ----------------------------------------------------------------
    def test_context(self):
        """Test the context manager functionality.

        Check that database access in context works, and vice versa
        out of context. The purpose of this test was originally to
        test a bespoke implementation of context magic methods worked,
        despite the code now inheriting this behaviour from the
        `sqlite3.Connection` class.

        This test makes no changes to the database and uses a separate
        connection from the one instantiated in setUp.
        """
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
        """Check sqlite3 connection attributes/methods are exposed.

        This test was introduced after the decision to expose the
        `sqlite3.Connection` API rather than wrap it. It's a simple
        check to ensure a sample method is exposed and becomes
        pointless in the event `execute` is implemented as a method
        directly in the `DB` class.
        """
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
        """Converts datetime to a string compatible with SQLite TEXT.

        This static method ensures datetime objects are stored
        correctly in the sqlite database. The specified storage
        format is:

            YYYY-MM-DD HH:MM
        """
        dt = datetime(*pydt)
        self.assertEqual(DB.pydt_to_dbdt(dt), dbdt)

    @data(*dt_examples)
    @unpack
    def test_dbdt_to_pydt(self, pydt, dbdt):
        """Converts SQLite TEXT datetime strings to py datetime.

        This test checks the inverse of `test_pydt_to_dbdt`.
        """
        dt = datetime(*pydt)
        self.assertEqual(DB.dbdt_to_pydt(dbdt), dt)

    def test_create(self):
        """Tests creation of a new database (schema).

        Method populates a fresh database.
        """
        try:
            DB.path_db = ':memory:'                # Temp db location
            db = DB()
            tables = db.tables()
            self.assertEqual(len(tables), 2)
            self.assertCountEqual(
                tables,
                ('quota_history', 'quota_monthly')
            )
            DB.path_db = self.path_refdb           # Reset db location
        except AssertionError as err:
            DB.path_db = self.path_refdb
            raise err
        except Exception as err:
            raise err

    @data(
        # 98 GB left of 100 GB allowance on 2000-01-01T18:00
        [(datetime(2001, 1, 1, 18), 98000000000, 100000000000)],
        [(datetime(2001, 1, 1, 18), 98000000000, 100000000000),
         (datetime(2001, 1, 1, 19), 97500000000, 100000000000)],
        [(datetime(2001, 1, 1, 18), 98000000000, 100000000000),
         (datetime(2001, 1, 2, 18), 97500000000, 100000000000)],
        [(datetime(2001, 1, 1, 18), 98000000000, 100000000000),
         (datetime(2002, 1, 1, 18), 97500000000, 100000000000)],
        [(datetime(2001, 1, 1, 18), 98000000000, 100000000000),
         (datetime(2002, 1, 2, 18), 97500000000, 100000000000)],
    )
    def test_insert_quota(self, quota_list):
        """Handles insertion of quota data.

        Method takes a quota timestamp, remainder and total, and
        inserts this information into the `quota_history` and
        `quota_monthly tables`.
        """
        db = self.db
        for quota in quota_list:
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
