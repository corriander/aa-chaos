"""Module containing unit tests relating to fetching data."""

import builtins
import unittest
import os
import sqlite3
import tempfile
from datetime import datetime
from collections import namedtuple

from unittest.mock import patch
from ddt import file_data, ddt
import pandas
import requests

from aachaos.get import BroadbandInfo, Quota, DB, History, Credentials

PATHD_TEST = os.path.dirname(__file__)
PATHD_TESTDATA = os.path.join(PATHD_TEST, 'data')
PATH_MINRESPONSE = os.path.join(
    PATHD_TESTDATA,
    'dummy_minimal_response.xml'
)
PATH_TESTDB = os.path.join(PATHD_TESTDATA, 'test_store.db')


class TestBroadbandInfo(unittest.TestCase):
    """Check the functionality of the BroadbandInfo class.

    BroadbandInfo encapsulates the API's XML response.
    """
    with open(PATH_MINRESPONSE, 'rb') as f:
        xml_minimal_response = f.read()

    @patch('aachaos.get.BroadbandInfo.parse')
    @patch('aachaos.get.BroadbandInfo.fetch')
    def test___init__(self, mock_fetch, mock_parse):
        mock_fetch.return_value = self.xml_minimal_response
        line_info = BroadbandInfo('any user', 'any pass')

        #import pdb; pdb.set_trace()
        mock_fetch.assert_called_with('any user', 'any pass')
        mock_parse.assert_called_with(mock_fetch.return_value)

    @patch('aachaos.get.BroadbandInfo.fetch')
    def test_parse(self, mock_fetch):
        """Parse creates a Quota object at `_quota` as a side-effect.
        """
        mock_fetch.return_value = self.xml_minimal_response
        line_info = BroadbandInfo('any user', 'any pass')
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

    # TODO: Use mock for this!
    # TODO: Move to memory?
    DB.path_db = PATH_TESTDB

    def setUp(self):
        # Create a connection to the reference database.
        self.db = DB()

    def test_select_from_quota_vw(self):
        """Returns contents of `quota_vw` as a DataFrame."""
        df = self.db.select_from_quota_vw()
        self.assertIsInstance(df, pandas.DataFrame)
        self.assertEqual(len(df), 68)

    def test_select_last_from_quota_vw(self):
        """Return the latest timestamp and percent value."""
        t = self.db.select_last_from_quota_vw()
        self.assertIsInstance(t, tuple)
        self.assertEqual(len(t), 2)
        self.assertEqual(t[0], datetime(2002, 1, 1, 18))
        self.assertEqual(t[1], 98)


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


@ddt
class TestCredentials(unittest.TestCase):

    def setUp(self):
        Credentials.auth_path = os.path.join(PATHD_TESTDATA, 'auth')

    def test_requests_compatibility(self):
        """Instances are used like requests.auth.HTTPBasicAuth.

        This test checks a well-formed instance is usable by requests
        and key behaviour looks right (namely that a basic auth HTTP
        header is added to the request when the instance is called).
        """
        auth = Credentials('TestingTerry', 'APassword')

        request = requests.Request(url='https://google.com',
                                   auth=auth)
        prepared_request = request.prepare()
        self.assertEqual(prepared_request.headers['Authorization'],
                         'Basic VGVzdGluZ1RlcnJ5OkFQYXNzd29yZA==')

    @file_data(
        os.path.join(PATHD_TESTDATA, 'credentials_parameters.json')
    )
    def test___init__(self, test_data):
        """Check instantiation of a Credentials object.

        A username and password are either provided as arguments or
        omitted, in which case the auth file is inspected.
        """
        expected = test_data['expected']

        if 'error' in expected:
            self.assertRaises(
                getattr(builtins, expected['error']),
                Credentials,
                *test_data['args']
            )

        else:
            inst = Credentials(*test_data['args'])
            self.assertEqual(inst.username, expected['username'])
            self.assertEqual(inst.password, expected['password'])

    def test_auth_file_bad_permissions(self):
        """Non-600 permissions should cause an exception."""
        Credentials.auth_path = os.path.join(PATHD_TESTDATA,
                                             'bad_auth')

        self.assertRaises(
            Credentials.FileNotSecure,
            Credentials,
            None,
            None
        )

        # However, this shouldn't matter if we explicitly provide.
        inst = Credentials('TestingTyra', 'AnotherPassword')
        self.assertEqual(inst.username, 'TestingTyra')
        self.assertEqual(inst.password, 'AnotherPassword')

    def test_auth_file_not_present(self):
        """An exception is raised if the auth file isn't present."""
        Credentials.auth_path = os.path.join(PATHD_TESTDATA,
                                             'non_existent_auth')

        self.assertRaises(
            Credentials.FileNotPresent,
            Credentials,
            None,
            None
        )

        # However, this shouldn't matter if we explicitly provide.
        inst = Credentials('TestingTyra', 'AnotherPassword')
        self.assertEqual(inst.username, 'TestingTyra')
        self.assertEqual(inst.password, 'AnotherPassword')


if __name__ == '__main__':
    unittest.main()
