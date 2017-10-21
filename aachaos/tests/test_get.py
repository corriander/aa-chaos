"""Module containing unit tests relating to fetching data."""

import builtins
import json
import unittest
import os
import sqlite3
import tempfile
from datetime import datetime
from collections import namedtuple

from unittest import mock
from ddt import file_data, ddt
import pandas as pd
import requests

from aachaos.get import BroadbandInfo, Quota, DB, History, Credentials

PATHD_TEST = os.path.dirname(__file__)
PATHD_TESTDATA = os.path.join(PATHD_TEST, 'data')
PATH_TESTDB = os.path.join(PATHD_TESTDATA, 'test_store.db')
SAMPLE_BROADBAND_INFO_RESPONSE_PATH = os.path.join(
    PATHD_TESTDATA,
    'sample_broadband_info_response.json'
)
with open(SAMPLE_BROADBAND_INFO_RESPONSE_PATH) as f:
    SAMPLE_BROADBAND_INFO_RESPONSE = json.load(f)


def mock_requests_get(*args, **kwargs):
    class MockResponse(object):
        def __init__(self):
            self.status_code = 200

        @property
        def content(self):
            return json.dumps(self.json)

        def json(self):
            return SAMPLE_BROADBAND_INFO_RESPONSE

    return MockResponse()


class TestBroadbandInfo(unittest.TestCase):
    """Check the functionality of the BroadbandInfo class.

    BroadbandInfo encapsulates the API's XML response.
    """

    def test___init__(self):
        inst = BroadbandInfo('any user', 'any pass')
        self.assertEqual(inst.auth.username, 'any user')
        self.assertEqual(inst.auth.password, 'any pass')

    @mock.patch('aachaos.get.BroadbandInfo.fetch')
    @mock.patch('aachaos.get.BroadbandInfo.parse')
    def test_quota(self, mock_parse, mock_fetch):
        """Lazy property fetching the quota info on demand.

        Creation of the quota object is in parse, hence is tested
        there.
        """
        inst = BroadbandInfo('any user', 'any pass')

        mock_fetch.assert_not_called()
        mock_parse.assert_not_called()
        mock_quota = mock.Mock()
        mock_fetch.return_value = SAMPLE_BROADBAND_INFO_RESPONSE
        mock_parse.return_value = mock_quota

        self.assertIs(inst.quota, mock_quota)

        mock_fetch.assert_called()
        mock_parse.assert_called_with(SAMPLE_BROADBAND_INFO_RESPONSE)

    def test_parse(self):
        """Parse creates a Quota object at `_quota` as a side-effect.
        """
        inst = BroadbandInfo()

        # Pre-check to ensure we parse is responsible for creating the
        # _quota attribute.
        self.assertRaises(AttributeError, getattr, inst, '_quota')

        inst.parse(SAMPLE_BROADBAND_INFO_RESPONSE)

        # Inspect the _quota attribute.
        self.assertIsInstance(inst._quota, Quota)
        self.assertEqual(inst._quota.rem, 3394211557)
        self.assertEqual(inst._quota.tot, 100000000000)
        self.assertEqual(inst._quota.tstamp,
                         datetime(2000, 5, 20, 11, 0, 0))

    @mock.patch('requests.get', side_effect=mock_requests_get)
    def test_fetch(self, mock_get):
        """Given Credentials, fetch returns the call response."""
        inst = BroadbandInfo()
        response_data = inst.fetch()

        # Check requests.get is invoked as expected
        mock_get.assert_called_with(
            'https://chaos2.aa.net.uk/broadband/info',
            auth=inst.auth
        )

        # Check response handling.
        self.assertEqual(response_data,
                         SAMPLE_BROADBAND_INFO_RESPONSE)


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
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 68)

    def test_select_last_from_quota_vw(self):
        """Return the latest timestamp and percent value."""
        t = self.db.select_last_from_quota_vw()
        self.assertIsInstance(t, tuple)
        self.assertEqual(len(t), 2)
        self.assertEqual(t[0], datetime(2002, 1, 1, 18))
        self.assertEqual(t[1], 98)


@mock.patch('aachaos.get.DB.select_from_quota_vw')
class TestHistory(unittest.TestCase):
    """Exercise the History data-retrieval class.

    History has a couple of properties which provide pandas TimeSeries
    containing usage and quota history.
    """

    df_quota_vw = pd.DataFrame(
        columns=('remaining', 'total', 'percent'),
        data=[
            (98123456789, 100000000000, 98.12345679),
            (96987654321, 100000000000, 96.98765432),
            (99999999900, 100000000000, 99.9999999),
            (98000000000, 100000000000, 98)
        ],
        index=pd.DatetimeIndex(
            ('2000-01-01 18:00', '2000-01-02 00:00',
             '2000-02-01 01:00', '2001-01-01 18:00'),
            name='timestamp'
        )
    )

    ts_quota = pd.Series(
        (100, 100, 100),
        index=pd.PeriodIndex(
            ('2000-01', '2000-02', '2001-01'), freq='M'
        )
    )

    ts_usage = pd.Series(
        (98123456789, 96987654321, 99999999900, 98000000000),
        index=pd.DatetimeIndex(
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
        self.assertIsInstance(quota, pd.Series)

    def test_usage(self, mock_select_from_quota_vw):
        """Quota returns a time-series of quota remainder."""
        mock_select_from_quota_vw.return_value = self.df_quota_vw
        history = History()
        usage = history.usage(units='B')
        self.assertIsInstance(usage, pd.Series)


@ddt
class TestCredentials(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        auth_path = os.path.join(PATHD_TESTDATA, 'auth')
        os.chmod(auth_path, 0o600)
        Credentials.auth_path = auth_path

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
