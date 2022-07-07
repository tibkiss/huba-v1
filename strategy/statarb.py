"""HUBA: Pair trading statistical arbitrage implementation using Kalman Filters.
Mean reversion strategy pair trading strategy from Ernie Chan's Quantitative Trading book.

C: 2012 - 2015 Tibor Kiss <tibor.kiss@gmail.com>
"""

from datetime import datetime
import math

from collections import deque

import numpy as np
import logging
log = logging.getLogger(__name__)

# Pyalgotrade imports
from pyalgotrade.broker import Order
from pyalgotrade.barfeed import Frequency
from pyalgotrade.utils.cache import memoize

# HUBA imports
from strategy import Strategy
from strategy.kalmanfilter import KalmanFilter
from tools import priceRound, reduceBars, downscaleBarsInTime, CSV_CACHE_DIR, DT_FMT
from tools.csv_tools import loadHistoricalBars, alignBarlist, logTradeToCSV, writeBarsToNTCSV, logDailyROIToCSV
from tools.workdays import add_workdays

from strategy.hurst import hurst
from strategy.adfuller import adfuller

class StatArbStrategyStates(object):
    """
      State transitions:
         IN@__init__ -> ST@_updatePositionState: when RiskManager refuses to enter
         IN@__init__ -> CL@_updatePositionState -> WE@onOrderUpdate: when the position is invalid, cleanup then wait for entry
         IN@__init__ -> WE@_updatePositionState -> EN@_enterTrade -> IT@onOrderUpdate -> EX@_exitTrade -> WE@onOrderUpdate
         IN@__init__ -> IT@_updatePositionState -> EX@_exitTrade -> WE@onOrderUpdate
    """
    Initial, Cleanup, WaitForEntry, Entering, InTrade, Exiting, Stopped = range(1, 8)

    @classmethod
    def stateToStr(cls, state, short=False):
        ret = ('UN', 'Unknown')

        if   state == cls.Initial:      ret = ('IN', 'Initial')
        elif state == cls.Cleanup:      ret = ('CL', 'Cleanup')
        elif state == cls.WaitForEntry: ret = ('WE', 'WaitForEntry')
        elif state == cls.Entering:     ret = ('EN', 'Entering')
        elif state == cls.InTrade:      ret = ('IT', 'InTrade')
        elif state == cls.Exiting:      ret = ('EX', 'Exiting')
        elif state == cls.Stopped:      ret = ('ST', 'Stopped')

        if short: return ret[0]
        else: return ret[1]


class StatArbStrategyDirection(object):
    """Direction for the pair of instr0, instr1.
    Long means: instr0 Long, instr1 Short
    Short means: instr0 Short, instr1 Long

    Invalid state is set when there is no active position.
    """
    Invalid, Long, Short = 0, 1, -1


class StatArbStrategy(Strategy):
    """Statistical arbitrage strategy implementation.
    Hello.
    """
    def __init__(self, pair, parms, now, brokerAgent):
        Strategy.__init__(self, '_'.join(pair), brokerAgent, now)

        self._pair = pair  # Instrument Pair: (Instr0, Instr1)
        self._parms = parms

        # State variable
        self._state = StatArbStrategyStates.Initial

        # Quantities for the positions
        self._qty = {pair[0]: None, pair[1]: None}

        # Position direction: Long, Short or Invalid
        # Set by the initPositionState based on the quantities
        self._direction = StatArbStrategyDirection.Invalid

        # Recorded bars for the spread calculation through onBars
        self._bars = {pair[0]: deque(maxlen=parms.zScoreUpdateBuffer), pair[1]: deque(maxlen=parms.zScoreUpdateBuffer)}
        self._firstBar = {pair[0]: None, pair[1]: None}
        self._lastBar = {pair[0]: None, pair[1]: None}

        # Historical bars for the Lookback Window, list of Bar instances
        self._lookbackBars = {pair[0]: None, pair[1]: None}
        # List of averaged bar values ((O+H+L+C)/4) represented
        # as scalars. This will be used for Kalman Filtering
        self._lookbackBarsAvgd = {pair[0]: None, pair[1]: None}

        # List of hedge ratios: i0 - i1 * hedgeRatio for each (i0, i1)
        self._hedgeRatios = []

        # Lookback Window statistics
        self._lookbackSpreadMean = None
        self._lookbackSpreadStd = None

        # Spread
        self._spread = None

        # Z-Score
        self._zScore = None
        self._zScoreUpdateDT = None

        # Trading permission. Set to false during earnings season
        self.tradeAllowed = True

        # Kalman Filter
        kalman_filter_delta = parms.kalmanFilterDelta
        self._log_debug("Initializing Kalman Filter with delta: %s", kalman_filter_delta)
        self._kf = KalmanFilter(delta=kalman_filter_delta)

        # Properties of the entry and exit, used to calculate profits
        # We cannot use self._qty for profit calculation as it will be
        # set to 0 when the close positions are filled
        self._entryPrice = {pair[0]: None, pair[1]: None}
        self._entryQty = {pair[0]: None, pair[1]: None}
        self._exitPrice = {pair[0]: None, pair[1]: None}

        # Daily statistics
        self._closedPosCnt = 0  # Increases by one when we close a position (pair)
        self._tradeCnt = 0      # Increases when a trade is made
        self._ROI = 0

        # Setup position state
        self._runGuarded(self._initStrategy, pair, parms)

    def _log_error(self, msg, *args, **kwargs):
        if log.isEnabledFor(logging.ERROR):
            fmt_str = "%s [%s] %s: %s" % (self._now.strftime(DT_FMT),
                                          StatArbStrategyStates.stateToStr(self._state, True), self.symbols, msg)
            log.error(fmt_str, *args, **kwargs)

    def _log_warning(self, msg, *args, **kwargs):
        if log.isEnabledFor(logging.WARNING):
            fmt_str = "%s [%s] %s: %s" % (self._now.strftime(DT_FMT),
                                          StatArbStrategyStates.stateToStr(self._state, True), self.symbols, msg)
            log.warning(fmt_str, *args, **kwargs)

    def _log_info(self, msg, *args, **kwargs):
        if log.isEnabledFor(logging.INFO):
            fmt_str = "%s [%s] %s: %s" % (self._now.strftime(DT_FMT),
                                          StatArbStrategyStates.stateToStr(self._state, True), self.symbols, msg)
            log.info(fmt_str, *args, **kwargs)

    def _log_debug(self, msg, *args, **kwargs):
        if log.isEnabledFor(logging.DEBUG):
            fmt_str = "%s [%s] %s: %s" % (self._now.strftime(DT_FMT),
                                          StatArbStrategyStates.stateToStr(self._state, True), self.symbols, msg)
            log.debug(fmt_str, *args, **kwargs)

    def _initStrategy(self, pair, parms):
        i0, i1 = self._pair[0], self._pair[1]

        # Register the position to the risk manager
        try:
            self._ba.riskManager.addPosition((i0, i1))
        except ValueError as e:
            self._log_warning('RiskManager refused to register the position: %s', e)
            self._log_warning('Position is NOT managed')
            self.stop()
            return

        # Load data for Lookback Window, calculate hedge ratio and the spread stats
        self._loadLookbackBars()
        self._updateHedgeRatio()
        self._updateSpreadMeanStd()

        # Setup current state
        self._updatePositionState()

        # Check the earnings calendar
        # We are not trading a week before and after earnings
        self._checkEarnings()

    def _updatePositionState(self):
        """Load the open position from the broker and set state"""
        i0, i1 = self._pair[0], self._pair[1]
        self._qty[i0] = self._broker.getShares(i0)
        self._qty[i1] = self._broker.getShares(i1)

        self._direction = StatArbStrategyDirection.Invalid

        if self._qty[i0] == 0 and self._qty[i1] == 0:
            self._state = StatArbStrategyStates.WaitForEntry
            self._log_debug("Initial share quantities are 0, state set to WaitForEntry")
        elif (self._qty[i0] > 0 and self._qty[i1] < 0) or (self._qty[i0] < 0 and self._qty[i1] > 0):
            self._state = StatArbStrategyStates.InTrade
            self._direction = StatArbStrategyDirection.Long if self._qty[i0] > 0 else StatArbStrategyDirection.Short
            self._entryPrice[i0] = self._broker.getAvgCost(i0)
            self._entryPrice[i1] = self._broker.getAvgCost(i1)
            self._entryQty[i0] = self._qty[i0]
            self._entryQty[i1] = self._qty[i1]
            self._log_debug("Positions are open (%s), state set to WaitForExit", self._qty)
        else:
            self._log_warning("Invalid share quantities (%s) returned from broker, closing and retrying", self._qty)

            self._state = StatArbStrategyStates.Cleanup
            self._closePosition(i0)
            self._closePosition(i1)

    def _checkEarnings(self):
        """Check the Earnings Calendar. If we are a week before or after an earnings release
        we disallow trading"""
        if self._parms.earningsCeaseFire is False:
            self._log_info("Earnings cease-fire is disabled!")
            return
        else:
            daysBeforeEarnings, daysAfterEarnings = self._parms.earningsCeaseFire
            earningsStartDate = add_workdays(self._ba.today, daysBeforeEarnings)
            earningsEndDate = add_workdays(self._ba.today, daysAfterEarnings)

            self._log_info("Checking for earnings for time window %s - %s (%d to %d days from today)",
                           earningsStartDate, earningsEndDate, daysBeforeEarnings, daysAfterEarnings)

            for i in self._pair:
                earnings = self._ba.get_earnings(i, earningsStartDate, earningsEndDate)
                if len(earnings):
                    self._log_info('Trading is not allowed due to earnings for %s: %s', i, earnings)
                    self.tradeAllowed = False

    def _loadLookbackBars(self):
        """Load the bars for the Lookback Window. The bars are relative from previous business day"""
        i0, i1 = self._pair[0], self._pair[1]

        endDate = add_workdays(self._ba.today, -1)  # Previous business day
        startDate = add_workdays(endDate, -1 * self._parms.lookbackWindow)

        bars0 = loadHistoricalBars(i0, startDate, endDate, Frequency.DAY, offline=self._ba.offline)
        bars1 = loadHistoricalBars(i1, startDate, endDate, Frequency.DAY, offline=self._ba.offline)

        self._log_debug("historicalBars[%s]: %s", i0, bars0)
        self._log_debug("historicalBars[%s]: %s", i1, bars1)

        aligned0, aligned1 = alignBarlist(bars0, bars1)

        self._lookbackBars[i0] = aligned0
        self._lookbackBars[i1] = aligned1

        self._log_debug("lookbackBars[%s]: %s", i0, self._lookbackBars[i0])
        self._log_debug("lookbackBars[%s]: %s", i1, self._lookbackBars[i1])

        self._log_info("Hist bars loaded: %s - %s (%d days)", startDate.strftime("%y-%m-%d"),
                                                              endDate.strftime("%y-%m-%d"),
                                                              self._parms.lookbackWindow)

    def _updateHedgeRatio(self):
        """Calculate beta or hedge ratio from the Lookback Window.
        i0 - i1 * hedgeRatio = 0"""
        i0, i1 = self._pair[0], self._pair[1]

        # Convert the Bars to scalars: the avg of OHLC
        self._lookbackBarsAvgd[i0] = np.array([(e.getAdjOpen() + e.getAdjHigh() + e.getAdjLow() + e.getAdjClose()) / 4
                                                for e in self._lookbackBars[i0]])
        self._lookbackBarsAvgd[i1] = np.array([(e.getAdjOpen() + e.getAdjHigh() + e.getAdjLow() + e.getAdjClose()) / 4
                                                for e in self._lookbackBars[i1]])

        self._log_debug('lookbackBarsAvgd[%s]: %s', i0, self._lookbackBarsAvgd[i0])
        self._log_debug('lookbackBarsAvgd[%s]: %s', i1, self._lookbackBarsAvgd[i1])

        # Apply Kalman Filter
        for x,y in zip(self._lookbackBarsAvgd[i0], self._lookbackBarsAvgd[i1]):
            if self._parms.logPrices:
                hedgeRatio, _, _ = self._kf.update(math.log(x), math.log(y))
            else:
                hedgeRatio, _, _ = self._kf.update(x, y)
            self._hedgeRatios.append(hedgeRatio)

        self._log_debug("hedgeRatios: %s", self._hedgeRatios)

        # Record the hedge ratio
        # lastBarDate = self._lookbackBars[i0][-1].getDateTime()
        # self._ba.addHedgeRatioDS(self._pair, lastBarDate, self._hedgeRatio)

        self._log_info("Latest hedge ratio is %.4f", self._hedgeRatios[-1])

    def _updateSpreadMeanStd(self):
        """Calculate the spread's mean and the std for the Lookback Window"""
        i0, i1 = self._pair[0], self._pair[1]

        if self._parms.logPrices:
            lookbackSpread = np.log(self._lookbackBarsAvgd[i0]) - np.log(self._lookbackBarsAvgd[i1]) * self._hedgeRatios[-1]
        else:
            lookbackSpread = self._lookbackBarsAvgd[i0] - self._lookbackBarsAvgd[i1] * self._hedgeRatios[-1]

        self._lookbackSpreadMean = lookbackSpread.mean()
        self._lookbackSpreadStd = lookbackSpread.std()

        if self._parms.hurstEnabled:
            H = hurst(lookbackSpread)
            if H < 0.5:
                self.tradeAllowed = True
            else:
                self._log_info("Hurst filter sets tradeAllowed to False")
                self.tradeAllowed = False

        if self._parms.adfullerEnabled:
            adf = adfuller(lookbackSpread, 0)
            if adf[0] < adf[4]['5%']:
                self.tradeAllowed = True
            else:
                self._log_info("ADFuller sets tradeAllowed to False")
                self.tradeAllowed = False

        self._log_info("Lookback Spread mean: %.4f stddev: %.4f", self._lookbackSpreadMean, self._lookbackSpreadStd)

    def _updateZScore(self):
        """Calculate the zScore for the spread"""
        i0, i1 = self._pair[0], self._pair[1]

        # Accumulate the bars
        bars0 = reduceBars(self._bars[i0])
        bars1 = reduceBars(self._bars[i1])

        # Create a mid value based on OHLC
        val0 = (bars0.getAdjOpen() + bars0.getAdjHigh() + bars0.getAdjLow() + bars0.getAdjClose()) / 4
        val1 = (bars1.getAdjOpen() + bars1.getAdjHigh() + bars1.getAdjLow() + bars1.getAdjClose()) / 4

        self._log_debug("%s reduced: %s <-- %s", i0, bars0, self._bars[i0])
        self._log_debug("%s reduced: %s <-- %s", i1, bars1, self._bars[i1])
        self._log_debug("%s midpoint: %s", i0, val0)
        self._log_debug("%s midpoint: %s", i1, val1)

        # Spread from the last X minutes
        if self._parms.logPrices:
            self._spread = math.log(val0) - math.log(val1) * self._hedgeRatios[-1]
        else:
            self._spread = val0 - val1 * self._hedgeRatios[-1]
        self._zScore = (self._spread - self._lookbackSpreadMean) / float(self._lookbackSpreadStd)
        self._zScoreUpdateDT = self._now

        # Add the values to the BrokerAgent's DataStream for the plot
        #self._ba.addSpreadDS(self._pair, self._now, self._spread)
        self._ba._plotter.addZScoreDS(self._pair, self._now, self._zScore)

        self._log_debug("Spread: %.2f (%s@%.2f %s@%.2f), Z: %.2f",
                        self._spread, i0, val0, i1, val1, self._zScore)
        if self._zScore > 5:
            self._log_info("Z-Score is too high: %.2f", self._zScore)

    def _calculateLimitPrice(self, lastPrice, action, priceIncrement=None, roundPrecision=None):
        if priceIncrement is None:
            priceIncrement = 0.01 if lastPrice >= 1.0 else 0.0001

        if roundPrecision is None:
            roundPrecision = 2 if lastPrice >= 1.0 else 4

        sign = 1 if action == Order.Action.BUY else -1
        limitPrice = priceRound(float(lastPrice + sign * (self._parms.entryOrderDistance * lastPrice)), roundPrecision, priceIncrement)

        return limitPrice

    def _enterTrade(self, short):
        i0, i1 = self._pair[0], self._pair[1]
        qty = {}
        lastPrice0 = self._lastBar[i0].getAdjClose()
        lastPrice1 = self._lastBar[i1].getAdjClose()

        # Calculate share quantities: For instrument 0 take the qty from risk manager
        # then calculate instrument 1 qty using the hedge ratio
        try:
            qty[i0] = self._ba.riskManager.addPosition((i0, i1), lastPrice0)
            qty[i1] = -1 * int((qty[i0] * lastPrice0) / lastPrice1)
        except ValueError as e:
            # Entry not allowed
            self._log_error("RiskManager refused to enter the trade")
            return

        if short:
            type = "short"
            action0, action1 = Order.Action.SELL, Order.Action.BUY
            qty[i0] *= -1
            qty[i1] *= -1
        else:
            type = "long"
            action0, action1 = Order.Action.BUY, Order.Action.SELL

        self._log_info("Enter %s: %s %d@%.2f %s %d@%.2f Z: %.2f",
                        type, i0, qty[i0], lastPrice0, i1, qty[i1], lastPrice1, self._zScore)

        # If trading is not allowed due to earnings log the fact and exit here
        # At this point StatArb's global state is not changed only RiskManager
        # registered the position. Deregister at RM and abort.
        if not self.tradeAllowed:
            self._log_info("Trading is not allowed. Not entering trade")
            self._ba.riskManager.removePosition((i0, i1))
            return

        self._direction = StatArbStrategyDirection.Short if short else StatArbStrategyDirection.Long
        self._state = StatArbStrategyStates.Entering

        if self._parms.entryOrderDistance is False or self._parms.entryOrderDistance is None: # need to be explicit in order to exclude 0 value here
            order0 = self._broker.createMarketOrder(action0, i0, abs(qty[i0]), goodTillCanceled=False)
            order1 = self._broker.createMarketOrder(action1, i1, abs(qty[i1]), goodTillCanceled=False)
        else:
            limitPrice0 = self._calculateLimitPrice(lastPrice0, action0, self._parms.limitPriceIncrements[0])
            limitPrice1 = self._calculateLimitPrice(lastPrice1, action1, self._parms.limitPriceIncrements[1])

            self._log_debug("entryOrderDistance=%s, lastPrice0=%s, limitPrice0=%s, lastPrice1=%s, limitPrice1=%s",
                            self._parms.entryOrderDistance, lastPrice0, limitPrice0, lastPrice1, limitPrice1)

            order0 = self._broker.createLimitOrder(action0, i0, limitPrice0, abs(qty[i0]), goodTillCanceled=False)
            order1 = self._broker.createLimitOrder(action1, i1, limitPrice1, abs(qty[i1]), goodTillCanceled=False)

        self._log_info("%s Entry order: %s", i0, order0)
        self._log_info("%s Entry order: %s", i1, order1)

        self._broker.placeOrder(order0)
        self._broker.placeOrder(order1)

    def _closePosition(self, instr):
        if self._qty[instr] == 0:
            self._log_warning("closePosition is called but qty is 0 for %s", instr)
            return

        # Based on the current qtys exit the trade
        action = Order.Action.SELL if self._qty[instr] > 0 else Order.Action.BUY

        # Create the exit order
        if self._parms.exitOrderDistance is False or self._parms.exitOrderDistance is None: # need to be explicit in order to exclude 0 value here
            order = self._broker.createMarketOrder(action, instr, abs(self._qty[instr]))
        elif not self._lastBar[instr]:
            self._log_warning("exitOrderDistance is set but there is no bar processed yet")
            self._log_warning("falling back to market order to exit the position")
            order = self._broker.createMarketOrder(action, instr, abs(self._qty[instr]))
        else:
            lastPrice = self._lastBar[instr].getAdjClose()
            instrumentPosition = self._pair.index(instr)
            limitPrice = self._calculateLimitPrice(lastPrice, action, self._parms.limitPriceIncrements[instrumentPosition])

            self._log_debug("exitOrderDistance=%s, lastPrice=%s, limitPrice=%s",
                            self._parms.entryOrderDistance, lastPrice, limitPrice)

            order = self._broker.createLimitOrder(action, instr, limitPrice, abs(self._qty[instr]))

        self._log_info("%s Exit order: %s", instr, order)

        # Place the exit orders
        self._broker.placeOrder(order)

    def _exitTrade(self):
        i0, i1 = self._pair[0], self._pair[1]

        # Register the entry order's properties
        lastPrice0 = self._lastBar[i0].getAdjClose()
        lastPrice1 = self._lastBar[i1].getAdjClose()

        self._log_info("Exiting trade. %s %d@%.2f %s %d@%.2f Z: %.2f",
                       i0, self._entryQty[i0], lastPrice0, i1, self._entryQty[i1], lastPrice1, self._zScore)

        self._state = StatArbStrategyStates.Exiting

        # Close the positions
        self._closePosition(i0)
        self._closePosition(i1)

        # Deregister the position at the RiskManager
        self._ba.riskManager.removePosition((i0, i1))

    def onBars(self, bar, instrument):
        """Record the bars and call updateZScore.
        To support daily bars, the updateZScore should be called even if only one
        bar is provided by day."""
        i0, i1 = self._pair[0], self._pair[1]
        zScoreUpdated = False

        self._log_debug("New bar: %s %s", instrument, bar)

        # Skip empty bars
        if bar.getVolume() == 0:
            return

        # Avoid trading penny stocks
        #if bar.getAdjClose() < 1.0:
        #    self._log_warning("Stock price for %s is bellow $1.0, stopping", instrument)
        #    self.stop()

        self._now = bar.getDateTime().astimezone(self._ba.EasternTZ)
        self._bars[instrument].append(bar)
        if self._firstBar[instrument] is None:
            self._firstBar[instrument] = bar
        self._lastBar[instrument] = bar

        # Record the close price for plotting
        self._ba._plotter.addPriceDS(instrument, bar.getDateTime(), bar.getAdjClose())

        len0, len1 = len(self._bars[i0]), len(self._bars[i1])

        if len0 > 0 and len1 > 0:
            if self._zScore is None:
                # The first zScore update of the day
                self._updateZScore()
                zScoreUpdated = True
                self._log_info('Spread: %.2f, Z-Score: %.2f', self._spread, self._zScore)
            else:
                timeDiff = self._now - self._zScoreUpdateDT

                self._log_debug("Time since last Z-Score update: %s", timeDiff)
                self._updateZScore()
                zScoreUpdated = True

        if zScoreUpdated:
            # Trade logic based on the actual state and Z-Score
            if self._state == StatArbStrategyStates.WaitForEntry and self._zScore >= self._parms.entryZScore:
                self._enterTrade(short=True)
            elif self._state == StatArbStrategyStates.WaitForEntry and self._zScore <= -1 * self._parms.entryZScore:
                self._enterTrade(short=False)
            elif self._state == StatArbStrategyStates.InTrade:
                if self._direction == StatArbStrategyDirection.Long and self._zScore >= -1 * self._parms.exitZScore:
                    self._exitTrade()
                elif self._direction == StatArbStrategyDirection.Short and self._zScore <= self._parms.exitZScore:
                    self._exitTrade()

    # In live trading if an order is filled onOrderUpdate() is called multiple (2 or 3) times.
    # Use memoize() to debounce onOrderUpdate, maxlen is set to avoid excessive memory usage in backtesting
    @memoize(size=100, lru=False)
    def onOrderUpdate(self, order):
        i0, i1 = self._pair[0], self._pair[1]

        instrument = order.getInstrument()

        if order.isCanceled():
            self._log_info("%s Order is cancelled", instrument)
        if order.isAccepted():
            self._log_debug("%s Order is accepted", instrument)
        if order.isFilled():
            action = order.getAction()
            price = order.getExecutionInfo().getPrice()
            qty = order.getQuantity()

            self._tradeCnt += 1
            self._log_info("%s Order filled with price: $%.2f, qty: %d", instrument, price, qty)

            if self._state not in (StatArbStrategyStates.Cleanup, StatArbStrategyStates.Entering,
                                   StatArbStrategyStates.Exiting):
                self._log_error("Invalid state in onOrderUpdate: %s", self._state)
                self.stop()
                return

            # Calculate the new stock quantities for the stock.
            # We cannot query the broker.getShares at this point, live trading account update has a delay
            if action == Order.Action.BUY:
                self._qty[instrument] += qty
            elif action == Order.Action.SELL:
                self._qty[instrument] -= qty
            else:
                self._log_error('Invalid action: %s', action)
                self.stop()
                return

            if self._state == StatArbStrategyStates.Cleanup:
                if self._qty[i0] == 0 and self._qty[i1] == 0:
                    #self._logTradeROI()

                    self._state = StatArbStrategyStates.WaitForEntry
                    self._direction = StatArbStrategyDirection.Invalid
                    self._entryPrice = {i0: None, i1: None}
                    self._entryQty = {i0: None, i1: None}
                    self._exitPrice = {i0: None, i1: None}
            elif self._state == StatArbStrategyStates.Entering:
                self._entryPrice[instrument] = price
                if action == Order.Action.BUY:
                    self._entryQty[instrument] = qty
                elif action == Order.Action.SELL:
                    self._entryQty[instrument] = qty * -1
                else:
                    self._log_error('Invalid action: %s', action)
                    self.stop()
                    return

                if self._qty[i0] != 0 and self._qty[i1] != 0:
                    self._state = StatArbStrategyStates.InTrade

                if not self._ba.live:
                    dateTime = order.getExecutionInfo().getDateTime()  # Datetime is only available in backtesting
                    self._ba._plotter.addBuySellDS(instrument, dateTime, price, action)
            elif self._state == StatArbStrategyStates.Exiting:
                self._exitPrice[instrument] = price

                # If both contracts are filled
                if self._qty[i0] == 0 and self._qty[i1] == 0:
                    self._logTradeROI()

                    # Reset the state variables
                    self._state = StatArbStrategyStates.WaitForEntry
                    self._direction = StatArbStrategyDirection.Invalid
                    self._entryPrice = {i0: None, i1: None}
                    self._entryQty = {i0: None, i1: None}
                    self._exitPrice = {i0: None, i1: None}

                # Register the trade for plotting in case of backtesting
                if not self._ba.live:
                    dateTime = order.getExecutionInfo().getDateTime()  # Datetime is only available in backtesting
                    self._ba._plotter.addBuySellDS(instrument, dateTime, price, action)
            else:
                self._log_error("Invalid state at onOrderUpdate: %d", self._state)
                self.stop()

    def _logTradeROI(self):
        """Logs the profit for entryPrice[i0] and entryPrice[i1]
           Called after:
             - Cleanup
             - Finished trade (both stocks of the pair is closed)
             - End of day

            On cleanup calculate the roi for the closed contract.
            After a finished trade calculate the roi, using both contracts.
            On EOD calculate the daily roi using daily trades and currently open contract if any.
        """
        # Entered when the last exit order is processed
        # Entry price is set in _exitTrade in order to accurately obtain
        # the fill price of the entry order.
        if self._state not in (StatArbStrategyStates.Cleanup, StatArbStrategyStates.Exiting):
            self._log_error("Invalid state at _logTradeROI: %s", StatArbStrategyStates.stateToStr(self._state))
            return

        i0, i1 = self._pair[0], self._pair[1]
        profit = {i0: None, i1: None}
        roi = {i0: None, i1: None}
        cap = {i0: None, i1: None}
        includeComm = True if self._ba.live else False  # With IB the closing positions does not include commission


        for i in self._pair:
            if self._entryQty[i] is not None:
                profit[i], roi[i], cap[i] = self._ba.calcProfit(self._entryPrice[i], self._exitPrice[i],
                                                                self._entryQty[i], includeComm)

        sumProfit = sumCap = 0
        for i in self._pair:
            if roi[i] is not None:
                sumProfit += profit[i]
                sumCap += cap[i]
        sumROI = 100 * sumProfit / sumCap

        self._log_info("Profit: %.2f + %.2f = %.2f, SumCap: %d", profit[i0], profit[i1], sumProfit, sumCap)
        self._log_info("ROI: %.2f + %.2f = %.2f%%", roi[i0], roi[i1], sumROI)

        # Log trade to trades CSV
        if self._ba.live:
            logTradeToCSV(self._ba.tag, self._now.strftime(DT_FMT), "_".join(self._pair),
                          self._entryPrice[i0], self._exitPrice[i0], self._entryQty[i0],
                          self._entryPrice[i1], self._exitPrice[i1], self._entryQty[i1],
                          sumProfit, sumROI)

        # Record the trade to daily profits
        self._closedPosCnt += 1
        self._ROI += sumROI

    def _logDailyROI(self):
        if self._state != StatArbStrategyStates.Stopped:
            self._log_error("Invalid state at _logDailyROI: %s", StatArbStrategyStates.stateToStr(self._state))
            return

        # Calculate EOD ROI
        i0, i1 = self._pair[0], self._pair[1]
        profit = {i0: 0, i1: 0}
        roi = {i0: 0, i1: 0}
        cap = {i0: 0, i1: 0}

        sumProfit = sumROI = sumCap = 0
        for i in self._pair:
            # Calculate the daily return, if:
            #  - we have open position and
            #  - we have historical prices for yesterday and
            #  - there were trades on the exchange today
            if self._qty[i] != 0 and self._lookbackBars[i] and self._lastBar[i]:
                if self._tradeCnt > 0:
                    # If currently in position and position is created today: calculate using entryPrice + dailyROI
                    profit[i], roi[i], cap[i] = self._ba.calcProfit(self._entryPrice[i],
                                                                    self._lastBar[i].getAdjClose(), self._qty[i])
                else:
                    # If currently in position and position is not created today: calculate using yesterday's adj close
                    if self._lookbackBars[i] is None or self._lastBar is None:
                        self._log_warning("No _lookbackBars or _lastBar for %s, daily ROI might be incomplete", i)
                    else:
                        profit[i], roi[i], cap[i] = self._ba.calcProfit(self._lookbackBars[i][-1].getAdjClose(),
                                                                        self._lastBar[i].getAdjClose(), self._qty[i])
                sumProfit += profit[i]
                sumROI += roi[i]
                sumCap += cap[i]

        if sumCap != 0:
            sumROI = 100 * sumProfit / sumCap

        sumROI += self._ROI  # Adding ROIs is just an approximation

        self._log_info("ClosedPosCnt: %d TradeCnt: %d InPosCap: %d",
                       self._closedPosCnt, self._tradeCnt, sumCap)
        self._log_info("Daily ROI: %.2f + (%.2f + %.2f) = %.2f%%",
                       self._ROI, roi[i0], roi[i1], sumROI)
        # Log daily roi to CSV
        if self._ba.live:
            logDailyROIToCSV(self._ba.tag, self._now.strftime(DT_FMT), "_".join(self._pair),
                             self._ROI, self._closedPosCnt, self._tradeCnt, sumCap, roi[i0], roi[i1], sumROI)

    def stop(self):
        """Called at EOD by the BrokerAgent"""
        if self._state != StatArbStrategyStates.Stopped:
            self._state = StatArbStrategyStates.Stopped

            self._logDailyROI()

