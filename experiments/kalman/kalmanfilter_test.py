__author__ = 'tiborkiss'

from matplotlib import pyplot as plt

from pyalgotrade.barfeed import Frequency

from tools.csv_tools import loadHistoricalBars, alignBarlist, logTradeToCSV, writeBarsToNTCSV
from tools.business_days import goback

import math
# import numpypy
import numpy as np
import statsmodels.api as sm

from datetime import datetime, timedelta
import pytz

from strategy.kalmanfilter import KalmanFilter

from IPython.frontend.terminal.embed import InteractiveShellEmbed
# Now create the IPython shell instance. Put ipshell() anywhere in your code
# where you want it to open.
ipshell = InteractiveShellEmbed()

# OLS
class OLSTest():
    def __init__(self, pair, startdate, enddate, lookback):
        self._pair = pair
        self.lookback = lookback
        self.today = startdate.date()
        self._enddate = enddate.date()

        self._OLSWindowBars = {self._pair[0]: None, self._pair[1]: None}
        self._OLSWindowBarsAvgd = {self._pair[0]: None, self._pair[1]: None}

        self._hedgeRatio = 0

    def _loadOLSWindowBars(self):
        """Load the bars for the OLS Window. The bars are relative from today"""
        i0, i1 = self._pair[0], self._pair[1]

        startDate = goback(self.today, self.lookback)

        bars0 = loadHistoricalBars(i0, startDate, self.today, Frequency.DAY)
        bars1 = loadHistoricalBars(i1, startDate, self.today, Frequency.DAY)

        # The bars are not in order this point, yahoo returns the data out of order
        bars0.sort(key=lambda bar: bar.getDateTime())
        bars1.sort(key=lambda bar: bar.getDateTime())

        aligned0, aligned1 = alignBarlist(bars0, bars1)

        self._OLSWindowBars[i0] = aligned0
        self._OLSWindowBars[i1] = aligned1

        # print "Historical bars loaded: %s - %s" % (startDate, endDate)

    def _updateHedgeRatio(self):
        """Calculate beta or hedge ratio from the OLS Window.
        i0 - i1 * hedgeRatio = 0"""
        i0, i1 = self._pair[0], self._pair[1]

        # Convert the Bars to scalars: the avg of OHLC
        self._OLSWindowBarsAvgd[i0] = np.array([(e.getAdjOpen() + e.getAdjHigh() + e.getAdjLow() + e.getAdjClose()) / 4
                                                for e in self._OLSWindowBars[i0]])
        self._OLSWindowBarsAvgd[i1] = np.array([(e.getAdjOpen() + e.getAdjHigh() + e.getAdjLow() + e.getAdjClose()) / 4
                                                for e in self._OLSWindowBars[i1]])

        # Fit the Ordinary Least Squares model
        model = sm.OLS(self._OLSWindowBarsAvgd[i0], self._OLSWindowBarsAvgd[i1])
        results = model.fit()
        self._hedgeRatio = results.params[0]

        # print "Hedge ratio is %.4f" % self._hedgeRatio

    def __iter__(self):
        return self

    def next(self):
        self._loadOLSWindowBars()
        self._updateHedgeRatio()

        self.today += timedelta(days=1)

        if self.today == self._enddate:
            raise StopIteration
        else:
            return (self.today, self._hedgeRatio,
                    self._OLSWindowBars[self._pair[0]][-1], self._OLSWindowBars[self._pair[1]][-1])


class KFTest():
    def __init__(self, pair, startdate, enddate, lookback):
        self._pair = pair
        self.lookback = lookback
        self.today = startdate.date()
        self._enddate = enddate.date()

        self._lookbackBars = {self._pair[0]: None, self._pair[1]: None}
        self._lookbackBarsAvgd = {self._pair[0]: None, self._pair[1]: None}

        self._kf = KalmanFilter(delta=0.0001)

        self._hedgeRatio = 0
        self._e = 0
        self._q = 0

    def _loadLookbackBars(self):
        """Load the bars for the OLS Window. The bars are relative from today"""
        i0, i1 = self._pair[0], self._pair[1]

        startDate = goback(self.today, self.lookback)

        bars0 = loadHistoricalBars(i0, startDate, self.today, Frequency.DAY)
        bars1 = loadHistoricalBars(i1, startDate, self.today, Frequency.DAY)

        # The bars are not in order this point, yahoo returns the data out of order
        bars0.sort(key=lambda bar: bar.getDateTime())
        bars1.sort(key=lambda bar: bar.getDateTime())

        aligned0, aligned1 = alignBarlist(bars0, bars1)

        # Convert the Bars to scalars: the avg of OHLC
        self._lookbackBars[i0] = np.array([(e.getAdjOpen() + e.getAdjHigh() + e.getAdjLow() + e.getAdjClose()) / 4
                                           for e in aligned0])
        self._lookbackBars[i1] = np.array([(e.getAdjOpen() + e.getAdjHigh() + e.getAdjLow() + e.getAdjClose()) / 4
                                           for e in aligned1])

    def _updateHedgeRatio(self):
        """Calculate beta or hedge ratio from the OLS Window.
        i0 - i1 * hedgeRatio = 0"""
        i0, i1 = self._pair[0], self._pair[1]

        for x, y in zip(self._lookbackBars[i0], self._lookbackBars[i1]):
            beta, e, q = self._kf.update(x, y)

            self._e = e
            self._q = q
            self._hedgeRatio = beta

    def __iter__(self):
        return self

    def next(self):
        self._loadLookbackBars()
        self._updateHedgeRatio()

        self.today += timedelta(days=1)

        if self.today == self._enddate:
            raise StopIteration
        else:
            return (self.today, self._hedgeRatio, self._e, self._q,
                    self._lookbackBars[self._pair[0]][-1], self._lookbackBars[self._pair[1]][-1])

if __name__ == '__main__':
    pair = ('EWA', 'EWC')
    lookback = 40

    startdate = datetime(2006, 4, 26, 8, 0, 0, 0, pytz.timezone('US/Eastern'))
    enddate = datetime(2012, 4, 9, 22, 0, 0, 0, pytz.timezone('US/Eastern'))

    olstest = OLSTest(pair, startdate, enddate, lookback)
    kftest = KFTest(pair, startdate, enddate, lookback)

    plots = {'dt': [], 'instr0': [], 'instr1': [],
             'hedgeRatio_ols' : [],  'proj_ols': [],
             'hedgeRatio_kf': [], 'proj_kf': [], 'e_kf': [], 'q_kf': []}

    plt.figure()
    for today, hedgeRatio, instr0, instr1 in olstest:
        plots['dt'].append(today)
        plots['instr0'].append(instr0.getAdjClose())
        plots['instr1'].append(instr1.getAdjClose())

        plots['hedgeRatio_ols'].append(hedgeRatio)
        plots['proj_ols'].append(instr1.getAdjClose() * hedgeRatio)

    for today, hedgeRatio, e, q, instr0, instr1 in kftest:
        plots['hedgeRatio_kf'].append(hedgeRatio)
        plots['proj_kf'].append(instr1 * hedgeRatio)
        plots['e_kf'].append(e)
        plots['q_kf'].append(q)


    #plt.plot(plots['dt'], plots['hedgeRatio_ols'], label='hedgeRatio_ols')
    #plt.plot(plots['dt'], plots['hedgeRatio_kf'], label='hedgeRatio_kf')

    plt.plot(plots['dt'], plots['instr0'], label='instr0')
    # plt.plot(plots['dt'], plots['instr1'], label='instr1')
    plt.plot(plots['dt'], plots['proj_ols'], label='proj_ols')
    plt.plot(plots['dt'], plots['proj_kf'], label='proj_kf')
    #plt.plot(plots['dt'], plots['e_kf'], label='e_kf')


    plt.legend()


    plt.show()

