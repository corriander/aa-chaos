"""Module provides a simple command-line interface.

Satisfies the following use-cases:

  - Updating the local data store.
  - Retrieving data from the local data store.
"""
import os
import argparse
from datetime import datetime
from collections import namedtuple

from aachaos import get, store, vis

T_ELAPSED_MIN = 10800 # s, minimum elapsed time.


class Main(object):

    path_fig = '/tmp/aachaos_usage_monitor.svg'
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
        if not self._sufficient_fetch_interval():
            print("Insufficient time has elapsed.")
            return

        credentials = get.Credentials(args.user, args.passwd)
        self.user, self.passwd = credentials.user, credentials.passwd

        quota = self._get_quota()

        db = store.DB()
        db.insert_quota(*quota)
        db.commit()

        # Generate the latest figure as a side-effect.
        Args = namedtuple('Args', 'month, file')
        args = Args(datetime.today().strftime('%Y-%m'), self.path_fig)
        self.plot(args)

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
