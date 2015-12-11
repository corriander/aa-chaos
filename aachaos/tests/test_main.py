"""Module containing unit tests relating to the "main" entry point."""

import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
from collections import namedtuple
import contextlib
import io

from ddt import ddt as DDT, data, unpack

import aachaos.main
import aachaos.get
from aachaos.tests.test_get import PATH_TESTDB


@DDT
class TestMain(unittest.TestCase):
    """Class is used to provide a command-line based user interface.

    Different use cases are provided via methods here and can be
    accessed by running the script with appropriate argument
    combinations.
    """

    def setUp(self):
        self.main = aachaos.main.Main()

    def tearDown(self):
        pass

    @patch('aachaos.main.vis.Plotter.plot_month')
    @patch('aachaos.main.Main._sufficient_fetch_interval')
    @patch('aachaos.main.Main._get_quota')
    @patch('aachaos.main.store.DB.insert_quota')
    def test_update(self, mock_insert, mock_call, mock_check,
                    mock_plot):
        """Check an update is fetched from the API and stored.

        Additionally, a side-effect is to generate a plot during this
        procedure.
        """
        # Database, API and interval check are mocked.
        #
        #   - Fetching from the API is assumed to work so we just
        #     return a sample `get.Quota` instance from
        #     `Main._get_quota()`
        #   - We don't actually care about writing to a database here,
        #     so just check the `store.DB.insert_quota` method is
        #     called correctly.
        #	- We don't want to actually check for the latest fetch so
        #     avoid this entirely by mocking the interval check.
        #   - We don't want to actually plot anything.
        quota = aachaos.get.Quota(
            datetime.today(),
            12345678987,
            100000000000
        )
        mock_call.return_value = quota
        mock_check.return_value = True

        args = namedtuple('Args', 'user, passwd')('a user', 'a pass')
        self.main.update(args)
        mock_insert.assert_called_with(*quota)
        mock_plot.assert_called_with(
            datetime.today().strftime('%Y-%m'),
            self.main.path_fig
        )

    def test_data(self):
        """Check data is returned to the shell.

        This function spits out the contents of the `quota_view`
        table. The `get.DB` method that returns this is mocked to
        return a constant sample. The data is a pandas dataframe, so
        this test is configured to reflect this.
        """
        aachaos.main.get.DB.db_path = PATH_TESTDB
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            # NOTE: Cannot use pdb in this context.
            self.main.data()
            last_row = out.getvalue().splitlines()[-3]

        # We expect the last entry in the test database, which is
        # currently:
        self.assertIn('2002-01-01 18:00:00', last_row)

    # ----------------------------------------------------------------
    # Internal methods
    # ----------------------------------------------------------------
    # _get_quota is not tested, this is a simple wrapper around
    # `get.Lineinfo`.
    @data(
        (2.5, 15, 3), (2.5, 7, 2), (2.5, 3, 1),
        (1.5, 15, 2), (1.5, 7, 2), (1.5, 3, 1),
        (0.5, 15, 1), (0.5, 7, 1), (0.5, 3, 1)
    )
    @unpack
    def test__get_minimum_interval(self, days, pc, interval):
        """Check interval changes towards the end of the month.

        Thresholds are 2 days or 10%, below which it increases in
        frequency to 2-hourly, followed by hourly after 1 day or 5%.

        Interval is measured in seconds.
        """
        main = self.main
        func = main._get_minimum_interval
        self.assertEqual(func(days*24*3600, pc), interval*3600)


if __name__ == '__main__':
    unittest.main()
