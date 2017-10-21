"""Module facilitates fetching account data into a simplified form.
"""
import os
import xml.etree.ElementTree as ET
from collections import namedtuple
from datetime import datetime

import pandas as pd
import requests

import aachaos.store
from aachaos.config import settings

URL_CHAOS = 'https://chaos2.aa.net.uk/'


class DatabaseEmptyException(Exception): pass


Quota = namedtuple('Quota', 'tstamp, rem, tot')


class BroadbandInfo(object):
    """Encapsulates a broadband/info CHAOS API call."""

    class BadResponse(Exception): pass

    def __init__(self, username=None, password=None):
        self.auth = Credentials(username, password)

    @property
    def quota(self):
        """Lazily evaluated quota information."""
        try:
            return self._quota
        except AttributeError:
            return self.parse(self.fetch())

    def fetch(self):
        """Fetch broadband/info JSON from the CHAOS API."""
        response = requests.get('{}broadband/info'.format(URL_CHAOS),
                                auth=self.auth)

        if response.status_code != 200:
            raise self.BadResponse(
                'HTTP {}'.format(response.status_code)
            )

        data = response.json()
        if 'error' in data:
            raise self.BadResponse('Error: {}'.format(data['error']))
        return data

    def parse(self, data):
        """Parse broadband information contained in JSON structure.

        Method stores the content in local attributes (currently
        limited to a Quota object assigned to `_quota`).
        """
        if len(data['info']) != 1:
            msg = "No. broadband elements != 1"
            raise NotImplementedError(msg)
        info = data['info'][0]

        # Create the quota object
        q_tstamp = datetime.strptime(
            info['quota_timestamp'],
            '%Y-%m-%d %H:%M:%S'
        )
        q_left = int(info['quota_remaining']) # bytes
        q_tot = int(info['quota_monthly']) # bytes
        self._quota = quota = Quota(q_tstamp, q_left, q_tot)
        return quota


class DB(aachaos.store.DB):
    """Extends `store.DB` with data retrieval methods."""

    def select_from_quota_vw(self):
        """Return contents of `quota_vw` as a pd DataFrame."""
        cursor = self.execute(
            "SELECT * FROM quota_vw ORDER BY timestamp ASC"
        )
        records = cursor.fetchall()

        column_names = [tup[0] for tup in cursor.description]
        df = pd.DataFrame.from_records(records,
                                       columns=column_names)
        df['timestamp'] = pd.DatetimeIndex(df['timestamp'])
        return df.set_index('timestamp')

    def select_last_from_quota_vw(self):
        cursor = self.execute(
            """
            SELECT timestamp, percent
            FROM quota_vw
            WHERE timestamp = (
                SELECT max(timestamp)
                FROM quota_vw
            )
            """
        )
        pair = cursor.fetchone()
        if pair is None:
            # Database is empty, probably because it's been relocated
            # or this is a fresh install. Raise an exception for this
            # special case.
            raise DatabaseEmptyException
        return (self.dbdt_to_pydt(pair[0]), pair[1])


class Credentials(requests.auth.HTTPBasicAuth):
    """Encapsulate credentials for API authentication.

    Credentials are either provided explicitly at runtime or retrieved
    from a plain text file with a "secure" (600) local file
    (configured separately).
    """

    class FileNotPresent(RuntimeError): pass
    class FileNotSecure(RuntimeError): pass

    auth_path = os.path.join(settings.xdg_config, __package__, 'auth')

    def __init__(self, username=None, password=None):
        if self._validate_credentials(username, password):
            self.username, self.password = username, password
        else:
            self.username, self.password = self.retrieve()

    @staticmethod
    def _validate_credentials(username, password):
        if username is not None and password is not None:
            return True
        elif username is not None:
            raise ValueError("No password provided.")
        elif password is not None:
            raise ValueError("No username provided.")

    def _auth_file_present(self):
        return os.path.isfile(self.auth_path)

    def _permissions_ok(self):
        return oct(os.stat(self.auth_path).st_mode & 0o777) == '0o600'

    def retrieve(self):
        if not self._auth_file_present():
            raise self.FileNotPresent
        elif not self._permissions_ok():
            raise self.FileNotSecure
        else:
            with open(self.auth_path, 'r') as f:
                return tuple(f.readline().strip().split(':'))


class History(object):
    """Load quota history from `quota_vw`.

    Provides panda DataFrame manipulations via properties.
    """

    units = {
        'GiB' : 1 / (1024 ** 3),
        'GB' : 1 / (1000 ** 3),
        'B' : 1
    }

    def __init__(self):
        self.db = DB()

    def quota(self, units='GB'):
        """The monthly quota (pd TimeSeries)."""
        unitlu = self.units
        df = self.db.select_from_quota_vw()
        return df.total.resample('1M', kind='period') * unitlu[units]

    def usage(self, units='GB'):
        """Quota remainder (pd TimeSeries)."""
        unitlu = self.units
        df = self.db.select_from_quota_vw()
        return df.remaining * unitlu[units]

    def by_month(self, month=None, units='GB'):
        """Return usage over a month period.

        Arguments
        ---------

            month : pandas.Period | string (default current)
                Month in (explicit) string format YYYY-MM

            units : string (default 'GB')
                Units of the data.
        """
        if month is None:
            month = datetime.today().strftime('%Y-%m')
        if not isinstance(month, pd.Period):
            month = pd.Period(month)

        # Get the source data and filter for the specified month.
        usage = self.usage(units)
        indexes = usage.index.map(
            lambda d: (d.year, d.month) == (month.year, month.month)
        )
        usage = usage[indexes]

        return usage
