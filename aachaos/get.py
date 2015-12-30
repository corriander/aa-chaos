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

URL_CHAOS = 'https://chaos.aa.net.uk/'


class DatabaseEmptyException(Exception): pass


Quota = namedtuple('Quota', 'tstamp, rem, tot')


class LineInfo(object):
    """Adapter for the aa.net.uk clueless API.

    The API is subject to change at the time of writing.
    """

    class AuthenticationError(Exception): pass

    def __init__(self, user, passwd):
        self.xml = xml = self.fetch(user, passwd)
        self.parse(xml)

    @property
    def quota(self):
        return self._quota

    def fetch(self, user, passwd):
        """Fetch the XML and load content into a LineInfo object."""
        response = requests.get('{}info'.format(URL_CHAOS),
                                auth=(user, passwd))
        xml = response.text
        # TODO: Move the following into own function when refactoring.
        root = ET.fromstring(xml)
        if root.get('error'):
            raise self.AuthenticationError("%s/%s" % (user, passwd))
        return xml

    def parse(self, xml):
        """Parse line information contained in an XML string.

        Method stores the content in local attributes (currently
        limited to a Quota object assigned to `_quota`).
        """
        root = ET.fromstring(xml)

        bb_lines = root.findall(
            './/{{{}}}broadband'.format(URL_CHAOS)
        )

        if len(bb_lines) != 1:
            msg = "No. broadband elements != 1"
            raise NotImplementedError(msg)

        # We should now have an element with information stored as
        # key:value attribute pairs.
        element = bb_lines[0]
        d = dict(element.items())

        # Create the quota object
        q_tstamp = datetime.strptime(
            d['quota-time'],
            '%Y-%m-%d %H:%M:%S'
        )
        q_left = int(d['quota-left']) # bytes
        q_tot = int(d['quota-monthly']) # bytes
        self._quota = Quota(q_tstamp, q_left, q_tot)

    @classmethod
    def credentials(cls, obj):
        if not isinstance(obj, Credentials):
            raise TypeError("Credentials object must be provided.")
        else:
            return cls(obj.user, obj.passwd)


class DB(aachaos.store.DB):
    """Extends `store.DB` with data retrieval methods."""

    def select_from_quota_vw(self):
        """Return contents of `quota_vw` as a pd DataFrame."""
        cursor = self.execute("SELECT * FROM quota_vw")
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


class Credentials(object):
    """Encapsulate authorisation/credentials functionality.

    Credentials are either provided at runtime or retrieved from a
    plain text file with a "secure" (600) local file (configured
    separately). By default, instances assume the latter unless
    credentials are explicitly provided.
    """

    class FileNotPresent(RuntimeError): pass
    class FileNotSecure(RuntimeError): pass

    auth_path = os.path.join(settings.xdg_config, __package__, 'auth')

    def __init__(self, user=None, passwd=None):
        if self._userpasswd_provided(user, passwd):
            self.user, self.passwd = user, passwd
        else:
            self.user, self.passwd = self.retrieve()

    @staticmethod
    def _userpasswd_provided(user, passwd):
        return user is not None and passwd is not None

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
