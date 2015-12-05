"""Module containing unit tests relating to fetching data."""

import unittest
import os
import sqlite3
import tempfile
from datetime import datetime
from collections import namedtuple

from unittest.mock import patch
from ddt import data, unpack, ddt as DDT
import pandas

from aachaos.get import LineInfo, Quota, DB, History

PATHD_TEST = os.path.dirname(__file__)
PATHD_TESTDATA = os.path.join(PATHD_TEST, 'data')
PATH_MINRESPONSE = os.path.join(
    PATHD_TESTDATA,
    'dummy_minimal_response.xml'
)

class TestLineInfo(unittest.TestCase):
    """Check the functionality of the LineInfo class.

    LineInfo encapsulates the API's XML response.
    """
    with open(PATH_MINRESPONSE, 'rb') as f:
        xml_minimal_response = f.read()

    @patch('aachaos.get.LineInfo.parse')
    @patch('aachaos.get.LineInfo.fetch')
    def test___init__(self, mock_fetch, mock_parse):
        mock_fetch.return_value = self.xml_minimal_response
        line_info = LineInfo('any user', 'any pass')

        #import pdb; pdb.set_trace()
        mock_fetch.assert_called_with('any user', 'any pass')
        mock_parse.assert_called_with(mock_fetch.return_value)

    @patch('aachaos.get.LineInfo.fetch')
    def test_parse(self, mock_fetch):
        """Parse creates a Quota object at `_quota` as a side-effect.
        """
        mock_fetch.return_value = self.xml_minimal_response
        line_info = LineInfo('any user', 'any pass')
        self.assertIsInstance(line_info._quota, Quota)
        self.assertEqual(line_info._quota.rem, 3394211557)


class TestDB(unittest.TestCase):
    """Exercise the DB wrapper/adapter class.

    This test case contains a number of general methods for analysing
    a sqlite3 database, comparing schema to a known one, etc. This
    class depends on an easily configurable database path to avoid
    wiping out a "production" database, load reference dataset(s),
    etc.
    """

    path_refdb = os.path.join(PATHD_TESTDATA, 'test_store.db')

    # TODO: Use mock for this!
    # TODO: Move to memory?
    DB.path_db = path_refdb

    def setUp(self):
        # Create a connection to the reference database.
        self.db = DB()

    def test_select_from_quota_vw(self):
        """Returns contents of `quota_vw` as a DataFrame."""
        df = self.db.select_from_quota_vw()
        self.assertIsInstance(df, pandas.DataFrame)
        self.assertEqual(len(df), 68)


@patch('aachaos.get.DB.select_from_quota_vw')
class TestHistory(unittest.TestCase):
    """Exercise the History data-retrieval class.

    History has a couple of properties which provide pandas TimeSeries
    containing usage and quota history.
    """

    df_quota_vw = pandas.DataFrame(
        columns=('remaining', 'total', 'percent'),
        data=[
            (98123456789, 100000000000, 98.12345679),
            (96987654321, 100000000000, 96.98765432),
            (99999999900, 100000000000, 99.9999999),
            (98000000000, 100000000000, 98)
        ],
        index=pandas.DatetimeIndex(
            ('2000-01-01 18:00', '2000-01-02 00:00',
             '2000-02-01 01:00', '2001-01-01 18:00'),
            name='timestamp'
        )
    )

    ts_quota = pandas.Series(
        (100, 100, 100),
        index=pandas.PeriodIndex(
            ('2000-01', '2000-02', '2001-01'), freq='M'
        )
    )

    ts_usage = pandas.Series(
        (98123456789, 96987654321, 99999999900, 98000000000),
        index=pandas.DatetimeIndex(
            ('2000-01-01 18:00', '2000-01-02 00:00',
             '2000-02-01 01:00', '2001-01-01 18:00'),
        )
    )

    # ----------------------------------------------------------------
    # Test Properties
    # ----------------------------------------------------------------
    def test_quota(self, mock_select_from_quota_vw):
        """Quota is a monthly quota value."""
        mock_select_from_quota_vw.return_value = self.df_quota_vw
        history = History()
        quota = history.quota(units='B')
        self.assertIsInstance(quota, pandas.Series)

    def test_usage(self, mock_select_from_quota_vw):
        """Quota returns a time-series of quota remainder."""
        mock_select_from_quota_vw.return_value = self.df_quota_vw
        history = History()
        usage = history.usage(units='B')
        self.assertIsInstance(usage, pandas.Series)

if __name__ == '__main__':
    unittest.main()
