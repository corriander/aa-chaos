"""Module provides plotting functionality.
"""
import os
import importlib
from datetime import datetime

import numpy as np
import pandas as pd

import matplotlib as mpl

import aachaos.get


class Plotter(object):

    def _import_pyplot(self, interactive=True):
        if interactive:
            # Use default backend
            pass
        else:
            mpl.use('agg')

        # Configure plotting style and assign module to attribute.
        self.plt =  importlib.import_module('matplotlib.pyplot')
        mpl.style.use('ggplot')

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
        self._import_pyplot(fpath is None)

        # TODO: Separate data generation from plotting.
        month = pd.Period(month)
        next_month = month + 1

        history = aachaos.get.History()
        usage = history.by_month(month, units='GB')
        #usage = history.usage('GB')
        quota = history.quota(units='GB')[month]
        #month = pd.Period(month)
        #next_month = month + 1
        #quota = quota[month]

        ## Strip the values outside of this month.
        #usage = usage[usage.index >= month.start_time]
        #usage = usage[usage.index < next_month.start_time]

        usage_linear = pd.Series(
           np.nan,
           index=pd.DatetimeIndex(
               start=month.start_time,
               end=next_month.start_time,
               freq='H'
           )
        )
        usage_linear[0] = quota
        usage_linear[-1] = 0
        usage_linear = usage_linear.interpolate()

        # Ensure we have a value at the start of the month.
        if usage.index[0] != month.start_time:
            a = usage_linear[usage_linear.index == month.start_time]
            usage = pd.concat((a, usage))

        fig, axes = self.plt.subplots()
        usage_linear.plot(ax=axes, color='0.6', linestyle='--')
        self._shade_weekends(axes)

        usage.plot(ax=axes, linestyle='-', color='#005E10')
        usage.plot(ax=axes, color='#A30A0A', style='.',
                   alpha=0.5)

        axes.set_ylabel('Quota [GB]')

        self._create(fpath)

        return fig, usage_linear

    # ----------------------------------------------------------------
    # Internal methods
    # ----------------------------------------------------------------
    def _create(self, fpath=None):
        # Thin wrapper around either savefig or show
        if fpath is not None and isinstance(fpath, str):
            self.plt.savefig(fpath)
        else:
            self.plt.show()

    def _shade_weekends(self, axes):
        # TODO: Work out how to avoid shading the white lines on the
        # ggplot style.
        xdata = [line.get_xdata() for line in axes.get_lines()]
        limit = {}
        for func in min, max:
            limit[func.__name__] = func(map(func, xdata)).start_time

        index = pd.DatetimeIndex(start=limit['min'], end=limit['max'],
                                 freq='D')

        df = pd.DataFrame(
            data=index.map(lambda d: d.weekday() >= 5),
            index=index,
            columns=('weekend',)
        )

        # Strip initial weekdays, we want the first entry to be a
        # weekend so it can be zipped using a single approach later.
        df = df[df.index >= df[df.weekend].index.min()]

        # Identify contiguous blocks (boolean) and assign an ID based
        # on the cumulative summation in a new column. The ID means we
        # can group it by block as well as status as weekend or not.
        we = df.weekend
        df['blockID'] = (we.shift(1) != we).astype(int).cumsum()

        # Group with a multi-index (weekend = 1, blockID = 2).
        df = df.reset_index()
        df = df.groupby(['weekend', 'blockID'])['index']
        df = df.apply(list)

        # We now have timestamps split into contiguous blocks,
        # classified by weekend/non-weekend. If we interleave these
        # two top-level lists (starting with weekend) and take the
        # head of each list/block of timestamps in each pair, we have
        # the start/end timestamps for each weekend.
        spans = []
        for wkend_tstamps, wkday_tstamps in zip(df[True], df[False]):
            spans.append((wkend_tstamps[0], wkday_tstamps[0]))

        for start, end in spans:
            axes.axvspan(xmin=start, xmax=end, color='0.80', alpha=0.5)

        return
