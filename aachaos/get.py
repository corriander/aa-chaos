"""Module facilitates fetching account data into a simplified form.
"""
# TODO: Encapsulate fetch and storage

import os
import xml.etree.ElementTree as ET
from collections import namedtuple
from datetime import datetime

import pandas
import requests

import aachaos.store

# How to derive this in ElementTree from the source?
URL_CHAOS = 'https://chaos.aa.net.uk/'

PATH_CFG_DEFAULT = os.path.join(
    os.getenv('HOME'),
    '.config',
    os.path.basename(os.path.dirname(__file__))
)
PATH_CFG = os.getenv('XDG_CONFIG_HOME', PATH_CFG_DEFAULT)

Quota = namedtuple('Quota', 'tstamp, rem, tot')

class LineInfo(object):
    """Adapter for the aa.net.uk clueless API.

    The API is subject to change at the time of writing.
    """

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
        return xml

    def parse(self, xml):
        """Parse line information contained in an XML string.

        Method stores the content in local attributes.
        """
        root = ET.fromstring(xml)

        # TODO: Build in authentication failure detection

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
        """Return contents of `quota_vw` as a pandas DataFrame."""
        cursor = self.execute("SELECT * FROM quota_vw")
        records = cursor.fetchall()

        column_names = [tup[0] for tup in cursor.description]
        df = pandas.DataFrame.from_records(records,
                                           columns=column_names)
        df['timestamp'] = pandas.DatetimeIndex(df['timestamp'])
        return df.set_index('timestamp')


class Credentials(object):
    """Encapsulate authorisation/credentials functionality.

    Credentials are either provided at runtime or retrieved from a
    plain text file with a "secure" (600) local file (configured
    separately). By default, instances assume the latter unless
    credentials are explicitly provided.
    """

    class FileNotPresent(RuntimeError): pass
    class FileNotSecure(RuntimeError): pass

    auth_path = os.path.join(PATH_CFG, 'auth')

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
        """The monthly quota (pandas TimeSeries)."""
        unitlu = self.units
        df = self.db.select_from_quota_vw()
        return df.total.resample('1M', kind='period') * unitlu[units]

    def usage(self, units='GB'):
        """Quota remainder (pandas TimeSeries)."""
        unitlu = self.units
        df = self.db.select_from_quota_vw()
        return df.remaining * unitlu[units]

