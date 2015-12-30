"""Module provides a simple command-line interface.

Satisfies the following use-cases:

  - Updating the local data store.
  - Retrieving data from the local data store.
"""
import os
import argparse
from datetime import datetime
from collections import namedtuple

import pandas as pd

from aachaos import get, store, vis
from aachaos.config import settings

T_ELAPSED_DEFAULT = 10800 # s, minimum elapsed time.


class Main(object):

    path_fig = settings.get('Path', 'Figure')
    # ----------------------------------------------------------------
    # External methods / use cases
    # ----------------------------------------------------------------
    def update(self, args):
        """Retrieve quota snapshot from API and store locally.

        Accepts an arguments object from argparse. argparse sets the
        default values (user=None, passwd=None) or passes the values
        specified on invocation. If either value is None,
        `get.Credentials` is used to retrieve stored user:pass combo.
        """
        try:
            if not self._sufficient_fetch_interval():
                print("Insufficient time has elapsed.")
                return
        except get.DatabaseEmptyException:
            # Special case of a new, empty database.
            pass

        credentials = get.Credentials(args.user, args.passwd)
        self.user, self.passwd = credentials.user, credentials.passwd

        quota = self._get_quota()

        db = store.DB()
        db.insert_quota(*quota)
        db.commit()

        # Generate the latest figure as a side-effect.
        plotter = vis.Plotter()
        plotter.plot_month(datetime.today().strftime('%Y-%m'),
                           self.path_fig)

    def data(self, args=None):
        """Retrieve data from local store."""
        # TODO: maybe allow optional file arg instead of stdout.
        # TODO: fix truncation of long data frames.
        # http://stackoverflow.com/q/19124601
        db = get.DB()
        print(db.select_from_quota_vw())

    def plot(self, args):
        """Plot usage data for the current month."""
        plotter = vis.Plotter()
        plotter.plot_month(month=args.month, fpath=args.file)

    # ----------------------------------------------------------------
    # Internal methods
    # ----------------------------------------------------------------
    def _get_quota(self):
        # Return the current quota info as a get.Quota instance.
        info = get.LineInfo(self.user, self.passwd)
        return info.quota

    def _get_minimum_interval(self, remaining_time, remaining_quota):
        # Minimum interval drops towards the end of the month.
        return min(
            self.__get_minimum_interval_time(remaining_time),
            self.__get_minimum_interval_quota(remaining_quota)
        )

    def __get_minimum_interval_time(self, remaining_time):
        if remaining_time < 1 * 24 * 3600:
            return 3600
        elif remaining_time < 2 * 24 * 3600:
            return 2 * 3600
        else:
            return T_ELAPSED_DEFAULT

    def __get_minimum_interval_quota(self, remaining_quota):
        x = remaining_quota
        if x < 5.0:
            return 3600
        elif x < 10.0:
            return 2 * 3600
        else:
            return T_ELAPSED_DEFAULT

    @staticmethod
    def _get_time_left(now):
        """Return time left in period."""
        delta = pd.Period(now.strftime('%Y-%m')).end_time - now
        return delta.total_seconds()

    def _get_time_now(self):
        # Required for mocking; can't mock datetime.
        return datetime.now()

    def _get_latest(self):
        """Get time and percent remaining from latest entry."""
        db = get.DB()
        time, rem = db.select_last_from_quota_vw()
        return (time, rem)

    # TODO: Change name to the less verbose 'can_update'
    def _sufficient_fetch_interval(self):
        # Be polite: we only need to check at most every hour, and for
        # most of the month, less than that.

        # Get basic stats from the last update and the current time.
        now = datetime.now()
        time, rem = self._get_latest()

        # Evaluate whether we have crossed the relevant thresholds
        t_elapsed = (now - time).total_seconds()
        t_left = self._get_time_left(now)
        return t_elapsed >  self._get_minimum_interval(t_left, rem)


if __name__ == '__main__':

    # Start by instantiating the main class so we can bind its methods
    main = Main()

    # Top level parser (main, named after this module)
    parser = argparse.ArgumentParser(prog='main')
    subparsers = parser.add_subparsers()
    # no top level args

    # Parser for the 'update' subcommand
    parser_update = subparsers.add_parser(
        'update',
        description="Fetch internet usage/quota."
    )
    parser_update.add_argument('--user', dest='user', type=str,
                               default=None)
    parser_update.add_argument('--pass', dest='passwd', type=str,
                               default=None)
    parser_update.set_defaults(func=main.update)

    # Parser for the 'data' subcommand
    parser_data = subparsers.add_parser(
        'data',
        description="Retrieve data from local store."
    )
    parser_data.set_defaults(func=main.data)
    # no args to data

    # Parser for the 'plot' subcommand
    parser_plot = subparsers.add_parser(
        'plot',
        description="Plot data in local store for this month."
    )
    parser_plot.add_argument(
        '--month',
        dest='month',
        type=str,
        default=datetime.today().strftime('%Y-%m')
    )
    parser_plot.add_argument('--file', dest='file', type=str,
                             default=None)
    parser_plot.set_defaults(func=main.plot)

    # Parse the command-line arguments and invoke the relevant bound
    # method/function with the arguments object (selects appropriate
    # subparser; yes, this is a bit obtuse).
    args = parser.parse_args()
    try:
        args.func(args)
    except AttributeError as err:
        if str(err) == "'Namespace' object has no attribute 'func'":
            raise RuntimeError("Missing subcommand.")
