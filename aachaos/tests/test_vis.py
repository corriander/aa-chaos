import unittest
from unittest.mock import patch

from ddt import ddt as DDT, data, unpack

import aachaos.vis
from aachaos.tests.test_get import PATH_TESTDB


@DDT
class TestPlotter(unittest.TestCase):

    aachaos.vis.aachaos.get.DB.path_db = PATH_TESTDB

    #def setUp(self):
    #	# Ensure no interactive plots are displayed.
    #	self.save_backend = aachaos.vis.mpl.get_backend()
    #	aachaos.vis.plt.switch_backend('agg')

    #def tearDown(self):
    #	aachaos.vis.plt.switch_backend(self.save_backend)

    @patch('aachaos.vis.plt.savefig')
    @patch('aachaos.vis.plt.show')
    @data(
        ('2001-01', None),
        ('2001-01', 'testpath.svg')
        # TODO: in-memory tests, may require modification to method.
    )
    @unpack
    def test_plot_month(self, month, fpath, mock_show, mock_save):
        self.skipTest("Skeleton implementation only.")
        plotter = aachaos.vis.Plotter()
        fig = plotter.plot_month(month, fpath)

        # Check figure creation is as expected.
        if fpath is None:
            mock_show.assert_called_with()
        else:
            mock_save.assert_called_with(fpath)

        xy = fig.axes[0].get_lines()[0].get_xydata()
        x = fig.axes[0].get_lines()[0].get_xdata()
        y = fig.axes[0].get_lines()[0].get_ydata()
