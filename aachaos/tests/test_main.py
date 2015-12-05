"""Module containing unit tests relating to the "main" entry point."""

import unittest
from unittest.mock import patch
from datetime import datetime
from collections import namedtuple
import contextlib
import io

import aachaos.main
import aachaos.get
from aachaos.tests.test_get import PATH_TESTDB


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

    @patch('aachaos.main.Main._sufficient_fetch_interval')
    @patch('aachaos.main.Main._get_quota')
    @patch('aachaos.main.store.DB.insert_quota')
    def test_update(self, mock_insert, mock_call, mock_check):
        """Check an update is fetched from the API and stored.
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
    # _sufficient_fetch_interval is not tested. This is a simple
    # wrapper around a comparison between the time elapsed (in
    # seconds) with a constant.
    @patch('aachaos.main.get.DB.select_max_timestamp')
    @patch('aachaos.main.Main._get_time_now')
    def test__get_interval(self, mock_now, mock_max):
        """Check interval evaluated between last stored quota and now.
        """
        mock_now.return_value = datetime(2000, 1, 1, 1)
        mock_max.return_value = datetime(2000, 1, 1, 0, 30)

        self.assertEqual(self.main._get_interval(), 30 * 60)


if __name__ == '__main__':
    unittest.main()
