import unittest

import logging
log=logging.getLogger(__name__)

import pytz

from datetime import datetime
import math
import copy

from pyalgotrade.broker import Broker, Order, MarketOrder, OrderExecutionInfo
from pyalgotrade.providers.interactivebrokers import ibbar

from strategy.brokeragent import BrokerAgent
from strategy.riskmanager import RiskManager
from strategy.statarb import StatArbStrategy, StatArbStrategyStates, StatArbStrategyDirection
from strategy.statarb_params import StatArbParams
from strategy.analyzer import Plotter

from mock import Mock, MagicMock, sentinel, patch, DEFAULT

class StatArbStrategy_BasicTest(unittest.TestCase):
    @patch('strategy.statarb.StatArbStrategy._initStrategy')
    def setUp(self, initStrategy):
        self._pair = ("SHY", "THC")
        self._broker = Mock(spec_set=Broker)
        self._ba = Mock(spec=BrokerAgent)
        self._ba.getBroker.return_value = self._broker
        self._ba.riskManager = Mock(spec_set=RiskManager)
        self._ba._plotter = Mock(spec_set=Plotter)
        self._ba.tag = sentinel.tag
        self._ba.live = sentinel.live
        self._ba.get_earnings = Mock()
        self._statArbStrategyParms = StatArbParams()
        self._now = datetime(2013, 11, 2, 11, 51, 02)
        self._ba.today = self._now.date()

        self._sa = StatArbStrategy(pair=self._pair, parms=self._statArbStrategyParms,
                                   now=self._now, brokerAgent=self._ba,)

        self._initStrategy = initStrategy

        logging.disable(logging.CRITICAL)

    def testConstructor(self):
        self.assertTrue(self._sa._pair == self._pair)
        self.assertTrue(self._sa._ba == self._ba)
        self._sa._ba.getBroker.assert_called_once_with()
        self.assertTrue(self._sa._broker == self._broker)
        self.assertTrue(self._sa._parms == self._statArbStrategyParms)

        self.assertTrue(self._sa._state == StatArbStrategyStates.Initial)
        self.assertTrue(self._sa._direction == StatArbStrategyDirection.Invalid)

        for instr in (self._pair[0], self._pair[1]):
            self.assertIsNone(self._sa._qty[instr])

            self.assertTrue(len(self._sa._bars[instr]) == 0)
            self.assertIsNone(self._sa._lookbackBars[instr])
            self.assertIsNone(self._sa._lookbackBarsAvgd[instr])

            self.assertIsNone(self._sa._entryPrice[instr])
            self.assertIsNone(self._sa._entryQty[instr])
            self.assertIsNone(self._sa._exitPrice[instr])

        self.assertTrue(self._sa._hedgeRatios == [])
        self.assertIsNone(self._sa._lookbackSpreadMean)
        self.assertIsNone(self._sa._lookbackSpreadStd)
        self.assertIsNone(self._sa._spread)
        self.assertIsNone(self._sa._zScore)

        self.assertTrue(self._sa._now == self._now)

        self.assertTrue(self._initStrategy.call_count == 1)

    @patch('strategy.statarb.StatArbStrategy.stop')
    @patch('strategy.statarb.StatArbStrategy._updatePositionState')
    @patch('strategy.statarb.StatArbStrategy._loadLookbackBars')
    @patch('strategy.statarb.StatArbStrategy._updateHedgeRatio')
    @patch('strategy.statarb.StatArbStrategy._updateSpreadMeanStd')
    @patch('strategy.statarb.StatArbStrategy._checkEarnings')
    def testInitStrategy(self, checkEarnings, updateSpreadMeanStd, updateHedgeRatio, loadLookbackBars,
                         updatePositionState, stop):
        self._sa._initStrategy(self._pair, self._statArbStrategyParms)
        self.assertTrue(updatePositionState.call_count == 1)
        self.assertTrue(loadLookbackBars.call_count == 1)
        self.assertTrue(updateHedgeRatio.call_count == 1)
        self.assertTrue(updateSpreadMeanStd.call_count == 1)
        self.assertTrue(checkEarnings.call_count == 1)
        self.assertFalse(stop.called)

        # If riskmanager refuses to register the position stop() should be called
        updatePositionState.reset_mock()
        loadLookbackBars.reset_mock()
        updateHedgeRatio.reset_mock()
        updateSpreadMeanStd.reset_mock()
        self._ba.riskManager.addPosition.side_effect = ValueError('Blabla')
        self._broker.getShares.side_effect = (-2, 2)
        self._sa._initStrategy(self._pair, self._statArbStrategyParms)
        self.assertFalse(updatePositionState.called)
        self.assertFalse(loadLookbackBars.called)
        self.assertFalse(updateHedgeRatio.called)
        self.assertFalse(updateSpreadMeanStd.called)
        stop.assert_called_once_with()

    @patch('strategy.statarb.StatArbStrategy.stop')
    @patch('strategy.statarb.StatArbStrategy._closePosition')
    def testPositionState(self, closePosition, stop):
        self._broker.reset_mock()

        # Check for 0 shares on both instrument, should set the state to WaitForEntry
        # getShares will be called for both instruments from the pair.
        stop.reset_mock()
        self._broker.getShares.side_effect = (0, 0)
        self._sa._updatePositionState()
        self.assertTrue(self._sa._state == StatArbStrategyStates.WaitForEntry)
        self.assertTrue(self._sa._direction == StatArbStrategyDirection.Invalid)
        self.assertFalse(stop.called)
        self.assertFalse(closePosition.called)

        # Valid pair trading scenarios: Long in instr0, Short in instr1 or the other way around.
        # Should wait for exit
        for shares in ((2, -2), (-4, 4), (3, -4), (-6, 7)):
            stop.reset_mock()
            self._broker.getShares.side_effect = shares
            self._sa._updatePositionState()
            if shares[0] > 0:
                self.assertTrue(self._sa._direction == StatArbStrategyDirection.Long)
            else:
                self.assertTrue(self._sa._direction == StatArbStrategyDirection.Short)
            self.assertTrue(self._sa._state == StatArbStrategyStates.InTrade)
            self.assertFalse(stop.called)
            self.assertFalse(closePosition.called)

        # Invalid scenarios, long or short with both instruments or one of the instrument is 0
        # Should set state to cleanup and report error via log.error
        for shares in ((0, 1), (2, 0), (-3, 0), (0, -4), (5, 5), (-6, -6)):
            stop.reset_mock()
            closePosition.reset_mock()
            self._broker.getShares.side_effect = shares

            self._sa._updatePositionState()

            self.assertTrue(self._sa._state == StatArbStrategyStates.Cleanup)
            self.assertTrue(self._sa._direction == StatArbStrategyDirection.Invalid)
            self.assertTrue(closePosition.called)

            closePosition.assert_any_call(self._pair[0])
            closePosition.assert_any_call(self._pair[1])

    def testClosePosition(self):
        self._broker.reset_mock()

        for qty in ((12, -24), (-50, 42), (-10, -10), (4, 6), (4, 0), (0, 1), (-5, 0), (0, -6), (0, 0)):
            self._sa._qty[self._pair[0]] = qty[0]
            self._sa._qty[self._pair[1]] = qty[1]

            # Try to close the first element of the pair
            self._broker.reset_mock()
            self._sa._closePosition(self._pair[0])
            if qty[0] == 0:
                self.assertFalse(self._broker.placeOrder.called)
                self.assertFalse(self._broker.createMarketOrder.called)
            else:
                if qty[0] > 0:
                    action = Order.Action.SELL
                else:
                    action = Order.Action.BUY

                self._broker.createMarketOrder.return_value = sentinel.marketorder
                self._broker.createMarketOrder.assert_called_once_with(action, self._pair[0], abs(qty[0]))
                self.assertTrue(self._broker.placeOrder.called)


            # Close the second element of the pair
            self._broker.reset_mock()
            self._sa._closePosition(self._pair[1])
            if qty[1] == 0:
                self.assertFalse(self._broker.placeOrder.called)
                self.assertFalse(self._broker.createMarketOrder.called)
            else:
                if qty[1] > 0:
                    action = Order.Action.SELL
                else:
                    action = Order.Action.BUY

                self._broker.createMarketOrder.return_value = sentinel.marketorder
                self._broker.createMarketOrder.assert_called_once_with(action, self._pair[1], abs(qty[1]))
                self.assertTrue(self._broker.placeOrder.called)


        # Check if invalid instrument raises exception
        self.assertRaises(KeyError, self._sa._closePosition, 'INVALID_INSTRUMENT')

    @patch('strategy.statarb.StatArbStrategy.stop')
    @patch('strategy.statarb.StatArbStrategy._logTradeROI')
    def testOnOrderUpdate(self, logTradeROI, stop):
        for i, live in enumerate((True, False)):
            self._ba.live = live

            execInfo1 = MagicMock(spec_set=OrderExecutionInfo)
            execInfo1.getPrice.return_value = 103.43

            # Start of the trade
            order1 = MarketOrder(Order.Action.BUY, self._pair[0], 12, False)
            orderExecInfo1 = OrderExecutionInfo(100.4, 12, 0, self._now)
            order1.setExecuted(orderExecInfo1)
            order2 = MarketOrder(Order.Action.SELL, self._pair[1], 24, False)
            orderExecInfo2 = OrderExecutionInfo(60.4, 24, 0, self._now)
            order2.setExecuted(orderExecInfo2)

            # Close of the trade
            order3 = MarketOrder(Order.Action.SELL, self._pair[0], 12, False)
            orderExecInfo3 = OrderExecutionInfo(120.4, 12, 0, self._now)
            order3.setExecuted(orderExecInfo3)
            order4 = MarketOrder(Order.Action.BUY, self._pair[1], 24, False)
            orderExecInfo4 = OrderExecutionInfo(40.4, 24, 0, self._now)
            order4.setExecuted(orderExecInfo4)

            # Valid states to enter onOrderUpdate: Cleanup, Entering, Exiting
            stop.reset_mock()
            logTradeROI.reset_mock()
            self._sa._state = StatArbStrategyStates.Cleanup
            self._sa._qty = {self._pair[0]: 100, self._pair[1]: 100}
            self._sa.onOrderUpdate(order1)
            self._sa.onOrderUpdate(order2)
            self.assertTrue(self._sa._state == StatArbStrategyStates.Cleanup)
            self.assertFalse(logTradeROI.called)
            self.assertFalse(stop.called)
            self._sa._qty = {self._pair[0]: 0, self._pair[1]: 42}
            order1 = copy.copy(order1)
            order2 = copy.copy(order2)
            self._sa.onOrderUpdate(order1)
            self._sa.onOrderUpdate(order2)
            self.assertTrue(self._sa._state == StatArbStrategyStates.Cleanup)
            self.assertFalse(logTradeROI.called)
            self.assertFalse(stop.called)
            self._sa._qty = {self._pair[0]: 12, self._pair[1]: 0}
            order1 = copy.copy(order1)
            order2 = copy.copy(order2)
            self._sa.onOrderUpdate(order1)
            self._sa.onOrderUpdate(order2)
            self.assertTrue(self._sa._state == StatArbStrategyStates.Cleanup)
            self.assertFalse(logTradeROI.called)
            self.assertFalse(stop.called)
            self._sa._qty = {self._pair[0]: -12, self._pair[1]: 24}
            order1 = copy.copy(order1)
            order2 = copy.copy(order2)
            self._sa.onOrderUpdate(order1)
            self._sa.onOrderUpdate(order2)
            self.assertTrue(self._sa._state == StatArbStrategyStates.WaitForEntry)
            self.assertFalse(logTradeROI.called)
            self.assertFalse(stop.called)

            # State in Entering
            self._sa._state = StatArbStrategyStates.Entering
            logTradeROI.reset_mock()
            self._sa._qty = {self._pair[0]: 0, self._pair[1]: 0}
            order1 = copy.copy(order1)
            self._sa.onOrderUpdate(order1)
            self.assertTrue(self._sa._state == StatArbStrategyStates.Entering)
            self.assertTrue(self._sa._qty[self._pair[0]] == 12)
            self.assertTrue(self._sa._qty[self._pair[1]] == 0)
            self.assertFalse(logTradeROI.called)
            self.assertFalse(stop.called)

            # Repeated order updates should not interfere with the state
            self._sa.onOrderUpdate(order1)
            self.assertTrue(self._sa._state == StatArbStrategyStates.Entering)
            self.assertTrue(self._sa._qty[self._pair[0]] == 12)
            self.assertTrue(self._sa._qty[self._pair[1]] == 0)
            self.assertFalse(logTradeROI.called)
            self.assertFalse(stop.called)

            # Post the second order, the state should change to WaitForExit
            order2 = copy.copy(order2)
            self._sa.onOrderUpdate(order2)
            self.assertTrue(self._sa._state == StatArbStrategyStates.InTrade)
            self.assertTrue(self._sa._qty[self._pair[0]] == 12)
            self.assertTrue(self._sa._qty[self._pair[1]] == -24)
            self.assertFalse(logTradeROI.called)
            self.assertFalse(stop.called)

            # Repeated orders should not affect the state
            self._sa.onOrderUpdate(order2)
            self.assertTrue(self._sa._state == StatArbStrategyStates.InTrade)
            self.assertTrue(self._sa._qty[self._pair[0]] == 12)
            self.assertTrue(self._sa._qty[self._pair[1]] == -24)
            self.assertFalse(logTradeROI.called)
            self.assertFalse(stop.called)

            # Close the trade, step 1
            self._sa._state = StatArbStrategyStates.Exiting
            self._sa.onOrderUpdate(order3)
            self.assertTrue(self._sa._state == StatArbStrategyStates.Exiting)
            self.assertTrue(self._sa._qty[self._pair[0]] == 0)
            self.assertTrue(self._sa._qty[self._pair[1]] == -24)
            self.assertFalse(logTradeROI.called)
            self.assertFalse(stop.called)

            # Repeat
            self._sa.onOrderUpdate(order3)
            self.assertTrue(self._sa._state == StatArbStrategyStates.Exiting)
            self.assertTrue(self._sa._qty[self._pair[0]] == 0)
            self.assertTrue(self._sa._qty[self._pair[1]] == -24)
            self.assertFalse(logTradeROI.called)
            self.assertFalse(stop.called)

            # Close the trade, step 2, the state should change to WaitForEntry and profit should be calculated
            self._sa.onOrderUpdate(order4)
            self.assertTrue(self._sa._state == StatArbStrategyStates.WaitForEntry)
            self.assertTrue(self._sa._qty[self._pair[0]] == 0)
            self.assertTrue(self._sa._qty[self._pair[1]] == 0)
            self.assertTrue(logTradeROI.called)
            self.assertFalse(stop.called)

            # Repeat
            logTradeROI.reset_mock()
            self._sa.onOrderUpdate(order4)
            self.assertTrue(self._sa._state == StatArbStrategyStates.WaitForEntry)
            self.assertFalse(logTradeROI.called)
            self.assertFalse(stop.called)
            self.assertTrue(self._sa._qty[self._pair[0]] == 0)
            self.assertTrue(self._sa._qty[self._pair[1]] == 0)

            # Check with invalid state, stop should be called
            for state in (StatArbStrategyStates.Initial, StatArbStrategyStates.Stopped,
                          StatArbStrategyStates.WaitForEntry, StatArbStrategyStates.InTrade):
                stop.reset_mock()
                orderX = copy.copy(order1)
                self._sa._state = state
                self._sa.onOrderUpdate(orderX)
                stop.assert_called_once_with()
                self.assertTrue(self._sa._qty[self._pair[0]] == 0)
                self.assertTrue(self._sa._qty[self._pair[1]] == 0)

    # TODO: Add onBars

    def testCheckEarnings(self):
        # Earnings cease fire enabled but not earnings present
        # given
        self._ba.get_earnings.reset_mock()
        self._ba.get_earnings.return_value = []
        self._sa._parms = StatArbParams(earningsCeaseFire=(-1, 1))
        # when
        self._sa._checkEarnings()
        # then
        self.assertTrue(self._ba.get_earnings.called)
        self.assertTrue(self._sa.tradeAllowed)


        # Earnings case fire enabled and earnings present
        # given
        self._ba.get_earnings.reset_mock()
        self._ba.get_earnings.return_value = [{'date': 'd', 'content': 'c', }, ]
        self._sa._parms._replace(earningsCeaseFire=(-1, 1))
        # when
        self._sa._checkEarnings()
        # then
        self.assertFalse(self._sa.tradeAllowed, "Trade is still allowed even though earnings presented")
        self.assertTrue(self._ba.get_earnings.called)

        # Earnings case fire disabled and earnings present (should ignore)
        # given
        self._sa.tradeAllowed = True
        self._ba.get_earnings.reset_mock()
        self._ba.get_earnings.return_value = [{'date': 'd', 'content': 'c', }, ]
        self._sa._parms = StatArbParams(earningsCeaseFire=False)
        # when
        self._sa._checkEarnings()
        # then
        self.assertFalse(self._ba.get_earnings.called)
        self.assertTrue(self._sa.tradeAllowed)

    @patch('strategy.statarb.StatArbStrategy._logDailyROI')
    def testStop(self, logDailyROI):
        self._ba.live = False
        self._sa._state = StatArbStrategyStates.Initial
        self._sa.stop()
        self.assertTrue(self._sa._state == StatArbStrategyStates.Stopped)
        logDailyROI.assert_called_once_with()

    def testEntryOrderDistanceDisabled(self):
        tz = pytz.timezone('US/Eastern')
        closePrice0 = 14
        closePrice1 = 210
        self._sa._lastBar = {self._sa._pair[0]: ibbar.Bar(datetime(2016, 8, 20, 13, 25, 5, 0, tz),
                                                          11.2, 14, 11.1, closePrice0, 110, 11.25, 12),
                             self._sa._pair[1]: ibbar.Bar(datetime(2016, 8, 20, 13, 25, 5, 0, tz),
                                                          201.2, 210, 201.1, closePrice1, 110, 201.25, 12)}

        lastHedgeRatio = 1.7
        qty0 = 333
        qty1 = int((qty0 * closePrice0) / closePrice1)

        self._sa._hedgeRatios = [1.5, 1.6, lastHedgeRatio]
        self._ba.riskManager.addPosition.return_value = qty0

        for short in (False, True):
            for value_to_disable in (False, None):
                self._broker.placeOrder.reset_mock()
                self._broker.createMarketOrder.reset_mock()
                self._broker.createLimitOrder.reset_mock()
                self._broker.createMarketOrder.side_effect = [sentinel.marketOrder1, sentinel.marketOrder2]
                self._sa._parms = StatArbParams(entryOrderDistance=value_to_disable)

                self._sa._enterTrade(short)

                if not short:
                    action0 = Order.Action.BUY
                    action1 = Order.Action.SELL
                else:
                    action0 = Order.Action.SELL
                    action1 = Order.Action.BUY

                self._broker.createMarketOrder.assert_any_call(action0, self._sa._pair[0], qty0, goodTillCanceled=False)
                self._broker.createMarketOrder.assert_any_call(action1, self._sa._pair[1], qty1, goodTillCanceled=False)

                self.assertTrue(self._broker.createMarketOrder.called)
                self.assertFalse(self._broker.createLimitOrder.called)
                self._broker.placeOrder.assert_any_call(sentinel.marketOrder1)
                self._broker.placeOrder.assert_any_call(sentinel.marketOrder2)


    def testEntryOrderDistanceEntry(self):
        tz = pytz.timezone('US/Eastern')
        closePrice0 = 14
        closePrice1 = 210
        self._sa._lastBar = {self._sa._pair[0]: ibbar.Bar(datetime(2016, 8, 20, 13, 25, 5, 0, tz),
                                                          11.2, 14, 11.1, closePrice0, 110, 11.25, 12),
                             self._sa._pair[1]: ibbar.Bar(datetime(2016, 8, 20, 13, 25, 5, 0, tz),
                                                          201.2, 210, 201.1, closePrice1, 110, 201.25, 12)}

        lastHedgeRatio = 1.7
        qty0 = 333
        qty1 = int((qty0 * closePrice0) / closePrice1)

        self._sa._hedgeRatios = [1.5, 1.6, lastHedgeRatio]
        self._ba.riskManager.addPosition.return_value = qty0

        for short in (False, True):
            for entryOrderDistance in (-0.6, -0.2, 0.1, 0.5):
                self._broker.placeOrder.reset_mock()
                self._broker.createMarketOrder.reset_mock()
                self._broker.createLimitOrder.reset_mock()
                self._broker.createLimitOrder.side_effect = [sentinel.limitOrder1, sentinel.limitOrder2]
                self._sa._parms = StatArbParams(entryOrderDistance=entryOrderDistance)

                self._sa._enterTrade(short)

                if not short:
                    action0 = Order.Action.BUY
                    action1 = Order.Action.SELL
                    targetPrice0 = closePrice0 + entryOrderDistance * closePrice0
                    targetPrice1 = closePrice1 - entryOrderDistance * closePrice1
                else:
                    action0 = Order.Action.SELL
                    action1 = Order.Action.BUY
                    targetPrice0 = closePrice0 - entryOrderDistance * closePrice0
                    targetPrice1 = closePrice1 + entryOrderDistance * closePrice1

                self._broker.createLimitOrder.assert_any_call(action0, self._sa._pair[0], targetPrice0, qty0, goodTillCanceled=False)
                self._broker.createLimitOrder.assert_any_call(action1, self._sa._pair[1], targetPrice1, qty1, goodTillCanceled=False)
                self.assertFalse(self._broker.createMarketOrder.called)
                self.assertTrue(self._broker.createLimitOrder.called)

                self._broker.placeOrder.assert_any_call(sentinel.limitOrder1)
                self._broker.placeOrder.assert_any_call(sentinel.limitOrder2)

