import os
import argparse
from datetime import datetime

from aachaos import get, store

T_ELAPSED_MIN = 10800 # s, minimum elapsed time.


class Main(object):

    def __init__(self, auth=()):
        """Accepts an optional 2-tuple containing user and pass.

        If credentials are not provided, they are fetched via
        `get.Credentials`.
        """
        if auth:
            self.user, self.passwd = auth
        else:
            auth =  get.Credentials(*auth)
            self.user, self.passwd = auth.user, auth.passwd

    # ----------------------------------------------------------------
    # External methods / use cases
    # ----------------------------------------------------------------
    def update(self):
        """Retrieve quota snapshot from API and store locally."""
        if not self._sufficient_fetch_interval():
            print("Insufficient time has elapsed.")
            return

        quota = self._get_quota()

        db = store.DB()
        db.insert_quota(*quota)
        db.commit()

    # ----------------------------------------------------------------
    # Internal methods
    # ----------------------------------------------------------------
    def _get_quota(self):
        # Return the current quota info as a get.Quota instance.
        info = get.LineInfo(self.user, self.passwd)
        return info.quota

    def _get_interval(self):
        # Return the time elapsed [s] since the last snapshot stored.
        db = get.DB()
        t_latest = db.select_max_timestamp()
        t_elapsed = self._get_time_now() - t_latest
        return t_elapsed.total_seconds()

    def _get_time_now(self):
        return datetime.now()

    def _sufficient_fetch_interval(self):
        # Be polite: check we're not hammering the API; there's no
        # point getting it more frequently than every hour.
        seconds_elapsed = self._get_interval()
        return seconds_elapsed > T_ELAPSED_MIN


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Fetch internet usage/quota."
    )
    parser.add_argument('--user', dest='user')
    parser.add_argument('--pass', dest='passwd')
    args = parser.parse_args()
    auth = args.user, args.passwd
    if tuple(filter(None, auth)) == auth:
        main = Main(auth=auth)
    else:
        main = Main()
    main.update()
