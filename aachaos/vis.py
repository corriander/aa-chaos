"""Module facilitates fetching account data into a simplified form.
"""
# TODO: Encapsulate fetch and storage

import os
from datetime import datetime

import numpy
import pandas

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

import aachaos.get

# Configure plotting style
mpl.style.use('ggplot')


class Plotter(object):

    # ----------------------------------------------------------------
    # External methods
    # ----------------------------------------------------------------
    def plot_month(self, month=datetime.today().strftime('%Y-%m'),
                   fpath=None):
        """Plot data for the specified month.

        If there is no data, no figure will be generated and a warning
        raised.

        Arguments
        ---------

            month : string (optional, default current month)
                Month specified as 'YYYY-MM'

            fpath : string (optional)
                Output file path (extension controls format). If not
                specified, default behaviour is to display the figure.
        """
        history = aachaos.get.History()
        usage = history.usage('GB')
        quota = history.quota('GB')
        month = pandas.Period(month)
        next_month = month + 1
        this_quota = quota[month]

        # Strip the values outside of this month.
        usage = usage[usage.index >= month.start_time]
        ts_actual_usage = usage[usage.index < next_month.start_time]

        ts_linear_usage = pandas.Series(
           numpy.nan,
           index=pandas.DatetimeIndex(
               start=month.start_time,
               end=next_month.start_time,
               freq='H'
           )
        )
        ts_linear_usage[0] = this_quota
        ts_linear_usage[-1] = 0
        ts_linear_usage = ts_linear_usage.interpolate()

        fig, axes = plt.subplots()
        ts_linear_usage.plot(ax=axes)
        ts_actual_usage.plot(ax=axes)
        self._plot(fpath)

        return fig

    # ----------------------------------------------------------------
    # Internal methods
    # ----------------------------------------------------------------
    def _plot(self, fpath=None):
        # Thin wrapper around either savefig or show
        if fpath is not None and isinstance(fpath, str):
            plt.savefig(fpath)
        else:
            plt.show()
