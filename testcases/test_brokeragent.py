import unittest
from mock import Mock, MagicMock, patch, sentinel
import logging
from datetime import datetime, date
import pytz

from pyalgotrade.bar import Bars
from pyalgotrade.providers.interactivebrokers import ibbroker, ibfeed, ibbar

from tools import DT_FMT
from config import StatArbPairsParams
from strategy.brokeragent import BrokerAgent
from strategy.statarb import StatArbStrategy
from strategy.riskmanager import RiskManager
from strategy.analyzer import Analyzer, Plotter

log=logging.getLogger(__name__)

class BrokerAgent_Test(unittest.TestCase):
    @patch('strategy.brokeragent.RiskManager', spec_set=RiskManager)
    @patch('strategy.brokeragent.Analyzer', spec_set=Analyzer)
    @patch('strategy.brokeragent.Plotter', spec_set=Plotter)
    @patch('strategy.brokeragent.BrokerAgent.subscribeFeed')
    @patch('strategy.brokeragent.BrokerAgent.addCSVWriter')
    def setUp(self, addCSVWriter, subscribeFeed, plotter, analyzer, riskManager):
        self._equity = 123456.78
        self._broker = MagicMock(spec_set=ibbroker.Broker)
        self._broker.getEquity.return_value = self._equity

        self._feed = MagicMock(spec_set=ibfeed.LiveFeed)
        self._live = True
        self._statArbConfig = StatArbPairsParams['Real']
        self._tag = sentinel.tag
        self._earnings = sentinel.earnings

        # Patched members
        self._addCSVWriter = addCSVWriter
        self._subscribeFeed = subscribeFeed
        self._analyzer = analyzer
        self._plotter = plotter
        self._riskManager = riskManager

        self._ba = BrokerAgent(self._feed, self._broker, self._live, self._statArbConfig, self._earnings, 1.0, self._tag)

        for pair in self._ba.pairs:
            sa =  MagicMock(StatArbStrategy)
            self._ba._positions[pair[0]] = sa
            self._ba._positions[pair[1]] = sa

    def testConstructor(self):
        # Verify input parameters
        self.assertTrue(self._feed == self._ba._feed)
        self.assertTrue(self._broker == self._ba.broker)
        self.assertTrue(self._live == self._ba.live)
        self.assertTrue(self._statArbConfig == self._ba._statArbConfig)
        self.assertTrue(self._earnings == self._ba._earnings)
        self.assertTrue(self._tag == self._ba.tag)

        # Derived from StatArbConfig
        self.assertTrue(self._statArbConfig.keys() == self._ba.pairs)

        # The subscribeFeed should be called for each instrument
        self.assertTrue(len(self._ba.pairs) > 0)
        count = 0
        for pair in self._ba.pairs:
            for instr in pair:
                self._subscribeFeed.assert_any_call(instr)
                count += 1
        self.assertTrue(self._subscribeFeed.call_count == count)

        # Check for Analyzer, Plotter creation
        self.assertTrue(self._analyzer.called)
        self.assertTrue(self._plotter.called)
        self.assertTrue(self._addCSVWriter.called)

        # Check for Broker's OrderUpdate event subscription
        self._broker.getOrderUpdatedEvent.assert_called_once_with()
        self._broker.getOrderUpdatedEvent.return_value.subscribe.called_once_with(self._ba._onOrderUpdate)

        # Check for equity dispatch
        self.assertTrue(self._ba.initialEquity == self._equity)

        # Riskmanager creation
        self._riskManager.assert_called_once_with(self._equity,
                                                  leverage=1.0,
                                                  maxPositionCount=len(self._ba.pairs),
                                                  instrPerPosition=2,
                                                  commission=self._ba.commission)

    def testGetBroker(self):
        self.assertTrue(self._ba.getBroker() == self._broker)

    def testGetEquity(self):
        self._broker.getEquity.reset_mock()

        # Calls back to broker
        self.assertTrue(self._ba.getEquity() == self._equity)
        self.assertTrue(self._broker.getEquity.called)

    @patch('time.sleep')
    def testSubscribeFeed(self, sleep):
        self._feed.subscribeRealtimeBars.reset_mock()
        self._feed.subscribeMarketBars.reset_mock()

        # Live is False. The subscription should not be dispatched.
        self._ba.live = False
        self._ba.subscribeFeed(sentinel.instr1)
        self.assertFalse(self._feed.subscribeRealtimeBars.called or self._feed.subscribeMarketBars.called)
        self.assertFalse(sleep.called)

        # Live is True then the subscription should be dispatched to the feed
        self._ba.live = True
        self._ba.subscribeFeed(sentinel.instr1)
        self.assertTrue(self._feed.subscribeRealtimeBars.called or self._feed.subscribeMarketBars.called)
        if self._feed.subscribeRealtimeBars.called:
            self._feed.subscribeRealtimeBars.assert_called_once_with(sentinel.instr1, useRTH_=False)
            sleep.assert_called_once_with(11)
        else:
            self._feed.subscribeMarketBars.assert_called_once_with(sentinel.instr1)
            self.assertFalse(sleep.called)

    def testUnsubscribeFeed(self):
        self._feed.unsubscribeRealtimeBars.reset_mock()
        self._feed.unsubscribeMarketBars.reset_mock()

        # Live is False. The subscription should not be dispatched.
        self._ba.live = False
        self._ba.unsubscribeFeed(sentinel.instr1)
        self.assertFalse(self._feed.unsubscribeRealtimeBars.called or self._feed.unsubscribeMarketBars.called)

        # Live is True then the subscription should be dispatched to the feed
        self._ba.live = True
        self._ba.unsubscribeFeed(sentinel.instr1)
        self.assertTrue(self._feed.unsubscribeRealtimeBars.called or self._feed.unsubscribeMarketBars.called)
        if self._feed.unsubscribeRealtimeBars.called:
            self._feed.unsubscribeRealtimeBars.assert_called_once_with(sentinel.instr1)
        else:
            self._feed.unsubscribeMarketBars.assert_called_once_with(sentinel.instr1)


    @patch('strategy.brokeragent.StatArbStrategy', spec_set=StatArbStrategy)
    def testCreateStrategy(self, statArbStrategy):
        # Initially set all the positions to None
        for pair in self._ba.pairs:
            for instr in pair:
                self._ba._positions[instr] = None

        currDT = datetime(2013, 9, 26, 15, 36, 10, 0, pytz.timezone("US/Eastern"))

        # Call the createStrategy
        self._ba._createStrategy(currDT)

        # Check if called for each pair only once
        for pair in self._ba.pairs:
            statArbStrategy.assert_any_call(pair, self._statArbConfig[pair], currDT, self._ba)

        # Check for call count
        self.assertTrue(statArbStrategy.call_count == len(self._ba.pairs))

        # Stop should not be called, since positions were not created initially
        self.assertFalse(statArbStrategy.stop_Guarded.called)
        self.assertFalse(statArbStrategy.stop.called)

        # Reset the mock and call the createStrategy second time
        statArbStrategy.reset_mock()

        currDT = datetime(2013, 9, 26, 15, 36, 20, 0, pytz.timezone("US/Eastern"))
        self._ba._createStrategy(currDT)

        # Check if called for each pair only once
        for pair in self._ba.pairs:
            statArbStrategy.assert_any_call(pair, self._statArbConfig[pair], currDT, self._ba)

        # Check for call count
        self.assertTrue(statArbStrategy.call_count == len(self._ba.pairs))

        # Stop should be called, since positions were already created
        #self.assertTrue(statArbStrategy.stop_Guarded.called)
        #self.assertTrue(statArbStrategy.stop_Guarded.call_count == len(self._ba.pairs))


    @patch('strategy.brokeragent.logEquityToCSV')
    @patch('strategy.brokeragent.BrokerAgent._createStrategy')
    @patch('strategy.brokeragent.BrokerAgent.stop')
    @patch('strategy.brokeragent.datetime.datetime')
    def testOnDayStartEnd(self, dt, stop, createStrategy, logEquityToCSV):
        self._now = datetime(2013, 11, 2, 13, 47, 11, 0, pytz.timezone('US/Eastern'))
        dt.now.return_value = self._now
        # Test with live=False
        self._ba.live = False

        self._ba.riskManager.reset_mock()

        # Bang
        currDT = datetime(2013, 9, 26, 15, 36, 30, 0, pytz.timezone("US/Eastern"))
        self._ba._onDayStart(currDT)

        # Check if the equity is being updated
        self._ba._analyzer.addDailyEquity.assert_called_once_with(self._broker.getEquity())
        self._ba._plotter.addEquityDS.assert_called_once_with(self._ba.today, self._broker.getEquity())
        self._ba.riskManager.setTradeCapital.assert_called_once_with(self._broker.getEquity())

        # Logger should not be called when live=False
        self.assertFalse(logEquityToCSV.called)

        # The Strategy should be recreated daily
        createStrategy.assert_called_once_with(currDT)

        # Stop should not be called
        self.assertFalse(stop.called)

        # Test with live=True
        createStrategy.reset_mock()
        logEquityToCSV.reset_mock()
        stop.reset_mock()
        self._ba.live = True

        # Reset the plotter, analyzer and riskmanager mocks
        self._ba.riskManager.reset_mock()

        # Bang
        currDT = datetime(2013, 9, 26, 15, 36, 40, 0, pytz.timezone("US/Eastern"))
        self._ba._onDayStart(currDT)

        # Check if the equity is being updated
        self._ba._analyzer.addDailyEquity.assert_called_once_with(self._broker.getEquity())
        self._ba._plotter.addEquityDS.assert_called_once_with(self._ba.today, self._broker.getEquity())
        self._ba.riskManager.setTradeCapital.assert_called_once_with(self._broker.getEquity())

        # Logger should not be called when live=False
        logEquityToCSV.assert_called_once_with(self._ba.tag, self._now.strftime(DT_FMT), self._broker.getEquity())

        # The Strategy should be recreated daily
        createStrategy.assert_called_once_with(currDT)

        self.assertFalse(stop.called)

        # Check day end: live=False
        stop.reset_mock()
        logEquityToCSV.reset_mock()
        self._ba.live = False

        self._ba._onDayEnd()

        self.assertFalse(logEquityToCSV.called)
        self.assertFalse(stop.called)

        # Check day end: live=True
        stop.reset_mock()
        logEquityToCSV.reset_mock()
        self._ba.live = True

        self._ba._onDayEnd()

        logEquityToCSV.assert_called_once_with(self._ba.tag, self._now.strftime(DT_FMT), self._equity)
        stop.assert_called_once_with()

    @patch('strategy.brokeragent.BrokerAgent._onDayStart')
    @patch('strategy.brokeragent.BrokerAgent._onDayEnd')
    def testOnBars(self, onDayEnd, onDayStart):
        # Check for dispatch based on hours: _onDayStart and _onDayEnd should be called
        # Analyzers, plotters should be called in RBH
        #
        i0 = self._ba._positions.keys()[0]
        i1 = self._ba._positions.keys()[1]

        tz = pytz.timezone('US/Eastern')

        # Day1: instrument 0 & 1. Day2: instrument 0 only
        bars = [
            # Day 1: before RTH
            Bars({i0: ibbar.Bar(datetime(2013, 7, 1, 7, 35, 5, 0, tz),
                                11.2, 11.4, 11.1, 11.3, 110, 11.25, 12),
                  i1: ibbar.Bar(datetime(2013, 7, 1, 7, 35, 5, 0, tz),
                                12.2, 12.4, 12.1, 12.3, 120, 12.25, 13),
                  }),

            # Day 1: inside RTH
            Bars({i0: ibbar.Bar(datetime(2013, 7, 1, 9, 30, 0, 0, tz),
                                11.2, 11.4, 11.1, 11.3, 110, 11.25, 12),
                  i1: ibbar.Bar(datetime(2013, 7, 1, 9, 30, 0, 0, tz),
                                12.2, 12.4, 12.1, 12.3, 120, 12.25, 13),
                  }),

            # Day 1: inside RTH
            Bars({i0: ibbar.Bar(datetime(2013, 7, 1, 9, 31, 7, 0, tz),
                                11.2, 11.4, 11.1, 11.3, 110, 11.25, 12),
                  i1: ibbar.Bar(datetime(2013, 7, 1, 9, 31, 7, 0, tz),
                                12.2, 12.4, 12.1, 12.3, 120, 12.25, 13),
                  }),

            # Day 1: after RTH
            Bars({i0: ibbar.Bar(datetime(2013, 7, 1, 16, 0, 5, 0, tz),
                                11.2, 11.4, 11.1, 11.3, 110, 11.25, 12),
                  i1: ibbar.Bar(datetime(2013, 7, 1, 16, 0, 5, 0, tz),
                                12.2, 12.4, 12.1, 12.3, 120, 12.25, 13),
                  }),
            # Day 2: before RTH
            Bars({i0: ibbar.Bar(datetime(2013, 7, 2, 8, 59, 59, 0, tz),
                                11.2, 11.4, 11.1, 11.3, 110, 11.25, 12),
                  }),
            # Day 2: inside RTH
            Bars({i0: ibbar.Bar(datetime(2013, 7, 2, 10, 15, 20, 0, tz),
                                11.2, 11.4, 11.1, 11.3, 110, 11.25, 12),
                  })
        ]

        self._ba.live = True

        # For each registered position create a mock object
        instruments = self._ba._positions.keys()
        for i in instruments:
            self._ba._positions[i] = MagicMock(spec_set=StatArbStrategy)

        # Day 1, Before RTH:
        # onDayStart, onDayEnd should not be called
        # should not dispatch to StatArbStrategy's onBars
        if not self._ba.live:
            self._ba._analyzer.reset_mock()
            self._ba._plotter.reset_mock()
        self._ba._onBars(bars[0])
        self.assertFalse(onDayStart.called)
        self.assertFalse(onDayEnd.called)
        for i in instruments:
            self.assertFalse(self._ba._positions[i].onBars_Guarded.called)
        if not self._ba.live:
            self.assertFalse(self._ba._analyzer.notifyAnalyzers.called)

        # Day 1, Inside regular trading hours. First bar should trigger the
        # today variable update and the _onDayStart routine call
        # The analyzers should be notified via notifyAnalyzers.
        # The bar must be dispatched to StratArbStrategy.onBars.
        if not self._ba.live:
            self._ba._analyzer.reset_mock()
        onDayStart.reset_mock()
        onDayEnd.reset_mock()
        self.assertTrue(self._ba.today is None)
        self._ba._onBars(bars[1])
        self.assertTrue(onDayStart.called)
        self.assertFalse(onDayEnd.called)
        # Only i0, i1's onBars should be called
        self._ba._positions[i0].onBars_Guarded.assert_called_once_with(bars[1][i0], i0)
        self._ba._positions[i1].onBars_Guarded.assert_called_once_with(bars[1][i1], i1)
        for i in [e for e in instruments if e not in (i0, i1)]:
            self.assertFalse(self._ba._positions[i].onBars_Guarded.called)
        if not self._ba.live:
            self.assertTrue(self._ba._analyzer.notifyAnalyzers.called)
        self.assertTrue(self._ba.today == date(2013, 7, 1))


        # Day 1, Inside regular trading hours: same day as before
        # Today variable should not updated, onDayStart should not be called
        # The rest is the same as above
        if not self._ba.live:
            self._ba._analyzer.reset_mock()
        onDayStart.reset_mock()
        onDayEnd.reset_mock()
        for i in instruments:
            self._ba._positions[i].reset_mock()
        self._ba._onBars(bars[2])
        self.assertFalse(onDayStart.called)
        self.assertFalse(onDayEnd.called)
        # Only i0, i1's onBars should be called
        self._ba._positions[i0].onBars_Guarded.assert_called_once_with(bars[2][i0], i0)
        self._ba._positions[i1].onBars_Guarded.assert_called_once_with(bars[2][i1], i1)
        for i in [e for e in instruments if e not in (i0, i1)]:
            self.assertFalse(self._ba._positions[i].onBars_Guarded.called)
        if not self._ba.live:
            self.assertTrue(self._ba._analyzer.notifyAnalyzers.called)
        self.assertTrue(self._ba.today == date(2013, 7, 1))

        # Day 1, After regular trading hours:
        # onDayEnd should be called, no bars should be dispatched
        if not self._ba.live:
            self._ba._analyzer.reset_mock()
        onDayStart.reset_mock()
        onDayEnd.reset_mock()
        for i in instruments:
            self._ba._positions[i].reset_mock()
        self._ba._onBars(bars[3])
        self.assertFalse(onDayStart.called)
        self.assertTrue(onDayEnd.called)
        for i in instruments:
            self.assertFalse(self._ba._positions[i].onBars_Guarded.called)
        if not self._ba.live:
            self.assertFalse(self._ba._analyzer.notifyAnalyzers.called)
        self.assertTrue(self._ba.today == date(2013, 7, 1))

        # Day 2, Before regular trading hours:
        # onDayStart, onDayEnd should not be called
        # should not dispatch to StatArbStrategy's onBars
        # Todays variable is changed on RTH
        if not self._ba.live:
            self._ba._analyzer.reset_mock()
        onDayStart.reset_mock()
        onDayEnd.reset_mock()
        for i in instruments:
            self._ba._positions[i].reset_mock()
        self._ba._onBars(bars[4])
        self.assertFalse(onDayStart.called)
        self.assertFalse(onDayEnd.called)
        for i in instruments:
            self.assertFalse(self._ba._positions[i].onBars_Guarded.called)
        if not self._ba.live:
            self.assertFalse(self._ba._analyzer.notifyAnalyzers.called)
        self.assertTrue(self._ba.today == date(2013, 7, 1))

        # Day 2, Inside regular trading hours:
        if not self._ba.live:
            self._ba._analyzer.reset_mock()
        onDayStart.reset_mock()
        onDayEnd.reset_mock()
        for i in instruments:
            self._ba._positions[i].reset_mock()
        self._ba._onBars(bars[5])
        self.assertTrue(onDayStart.called)
        self.assertFalse(onDayEnd.called)
        self._ba._positions[i0].onBars_Guarded.assert_called_once_with(bars[5][i0], i0)
        for i in [e for e in instruments if e != i0]:
            self.assertFalse(self._ba._positions[i].onBars_Guarded.called)
        if not self._ba.live:
            self.assertTrue(self._ba._analyzer.notifyAnalyzers.called)
        self.assertTrue(self._ba.today == date(2013, 7, 2))

    def testOnOrderUpdate(self):
        # Call onOrderUpdate for a non-registered instrument
        order = MagicMock(ibbroker.Order)
        order.getInstrument.return_value = 'Non-existent'

        for k in self._ba._positions.keys():
            self._ba._positions[k] = MagicMock(spec_set=StatArbStrategy)

        self._ba._onOrderUpdate(self._broker, order)

        # None of the positions onOrderUpdate should be called
        for k in self._ba._positions.keys():
            self.assertFalse(self._ba._positions[k].onOrderUpdate_Guarded.called)

        # Try it with valid instruments, should dispatch properly
        for instr in self._ba._positions:
            order.getInstrument.return_value = instr
            self._ba._onOrderUpdate(self._broker, order)

            self._ba._positions[instr].onOrderUpdate_Guarded.assert_called_once_with(order)

    @patch('strategy.brokeragent.BrokerAgent.stop')
    @patch('strategy.brokeragent.sleep')
    def testRun(self, sleep, stop):
        self._feed.reset_mock()
        self._broker.reset_mock()

        self._broker.stopDispatching.side_effect = (False, False, True)
        self._feed.stopDispatching.side_effect = (False, True, True)

        self._ba.run()

        self._feed.getNewBarsEvent.return_value.subscribe.assert_called_once_with(self._ba._onBars)
        self._feed.start.assert_called_once_with()
        self._broker.start.assert_called_once_with()

        self.assertTrue(self._feed.stopDispatching.call_count == 3)
        self.assertTrue(self._broker.stopDispatching.call_count == 3)

        self.assertTrue(self._feed.dispatch.call_count == 1)
        self.assertTrue(self._broker.dispatch.call_count == 2)

        stop.assert_called_once_with()

    def testStop(self):
        # Test with live=False, positions set
        self._ba.live = False

        self._broker.reset_mock()
        self._feed.getNewBarsEvent.return_value.unsubscribe.reset_mock()
        self._feed.reset_mock()

        for k in self._ba._positions.keys():
            self._ba._positions[k] = MagicMock(spec_set=StatArbStrategy)

        self._ba.stop()

        # Should be only called in non-live
        self.assertTrue(self._feed.getNewBarsEvent.return_value.unsubscribe.called)
        self.assertTrue(self._ba._stopped)

        # TODO FIXME
        #for k in self._ba._positions.keys():
        #    self.assertTrue(self._ba._positions[k].stop.called)

        self._broker.stop.assert_called_once_with()
        self._feed.stop.assert_called_once_with()

        self._broker.join.assert_called_once_with()
        self._feed.join.assert_called_once_with()

        # Test with live=True, positions uninitialized
        self._ba.live = True

        self._broker.reset_mock()
        self._feed.getNewBarsEvent.return_value.unsubscribe.reset_mock()
        self._feed.reset_mock()

        for k in self._ba._positions.keys():
            self._ba._positions[k] = None

        self._ba.stop()

        # Already stopped
        self.assertFalse(self._broker.stop.called)
        self.assertFalse(self._feed.stop.called)

        self._ba._stopped = False
        self._ba.stop()

        self._broker.stop.assert_called_once_with()
        self._feed.stop.assert_called_once_with()

        self._broker.join.assert_called_once_with()
        self._feed.join.assert_called_once_with()

        # Should be only called in live
        self.assertFalse(self._feed.getNewBarsEvent.return_value.unsubscribe.called)

        self._broker.stop.assert_called_once_with()
        self._feed.stop.assert_called_once_with()

        self._broker.join.assert_called_once_with()
        self._feed.join.assert_called_once_with()
