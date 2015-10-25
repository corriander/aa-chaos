"""Module facilitates fetching account data into a simplified form.

Acts as an adapter to the (at time of writing: changing) chaos API.
"""

import requests
import xml.etree.ElementTree as ET
from collections import namedtuple
from datetime import datetime

# How to derive this in ElementTree from the source?
URL_CHAOS = 'https://chaos.aa.net.uk/'

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
