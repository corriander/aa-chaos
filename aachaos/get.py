"""Module facilitates fetching account data into a simplified form.

Acts as an adapter to the (at time of writing: changing) chaos API.
"""

import os
import requests
import xml.etree.ElementTree as ET
from collections import namedtuple
from datetime import datetime

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
