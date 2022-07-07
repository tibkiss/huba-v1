
import logging
log = logging.getLogger(__name__)

import datetime, pytz
from time import sleep

from pyalgotrade.broker import backtesting
from pyalgotrade.providers.interactivebrokers import ibbroker
from pyalgotrade.barfeed import Frequency

from tools import DT_FMT
from tools import RealistFillStrategy
from tools.csv_tools import BarsToCSV, CSV_CACHE_DIR
from strategy.riskmanager import RiskManager
from strategy.statarb import StatArbStrategy
from analyzer import Analyzer, Plotter
from tools.csv_tools import logEquityToCSV

class BrokerAgent(object):
    """Broker Agent class.

    Customized version of pyalgotrade.strategy class to handle huba's strategies.
    Uses pyalgotrade.barfeed ibbroker and backtestingbroker blah
    """
    EasternTZ = pytz.timezone('US/Eastern')
    RTHStart = datetime.time(9, 30)
    RTHEnd = datetime.time(16, 00)

    def __init__(self, feed, broker, live, statArbConfig, earnings, leverage=1.0, tag='', offline=False):
        pairs = statArbConfig.keys()

        self.live = live   # Set to True in case of live-trade
        self.tag = tag
        self.pairs = pairs
        self.offline = offline
        self._earnings = earnings

        self.commission = ibbroker.FlatRateCommission()

        if broker is None:
            broker = backtesting.Broker(10000, feed, self.commission)
            broker.setUseAdjustedValues(True)
            broker.setFillStrategy(RealistFillStrategy())
        self.broker = broker

        self.initialEquity = broker.getEquity()

        self.today = None  # Today is set initially and updated by onBars to reflect the current date to the strategy
        self._currentHour = None  # For hourly tasks

        self._feed = feed
        self._statArbConfig = statArbConfig

        self._analyzer = Analyzer(broker)
        self._plotter = Plotter(pairs)

        self._stopped = False

        self.processed_bars = 0

        self.csv_writer = {}

        # Subscribe to order updates
        self.broker.getOrderUpdatedEvent().subscribe(self._onOrderUpdate)

        log.info("Creating positions and subscribing realtime feeds")
        self._positions = {}
        for pair in self.pairs:
            # The positions will be created by the _createStrategy()
            self._positions[pair[0]] = None
            self._positions[pair[1]] = None

            # If live subscribe for realtime bars
            self.subscribeFeed(pair[0])
            self.subscribeFeed(pair[1])

            self.addCSVWriter(pair[0])
            self.addCSVWriter(pair[1])


        # Initial equity and leverage is used in the RiskManager and the plotter
        self.initialEquity = self.getEquity()
        self.leverage = leverage

        # RiskManager
        self.riskManager = RiskManager(self.initialEquity, leverage=leverage,
                                       maxPositionCount=len(pairs), instrPerPosition=2,
                                       commission=self.commission)

        # Done
        log.info("Broker agent initialized")

    def calcProfit(self, entryPrice, exitPrice, qty, includeComm=False):
        """Calculate profit, roi and capital based on
           the entry & exit prices, and qty (signed).
           If qty is negative profit is calculated for short position
        """
        capital = entryPrice * abs(qty)
        profit = (exitPrice - entryPrice) * qty

        if includeComm:
            profit -= self.commission.calculate(None, entryPrice, abs(qty))

        roi = 100 * profit / capital

        return profit, roi, capital

    def getBroker(self):
        # Needed by pyalgotrade's stratanalyzer
        return self.broker

    def getEquity(self):
        return self.broker.getEquity()

    def getResult(self):
        # Needed by the optimizer
        return self.broker.getEquity()

    def get_earnings(self, symbol, start_date, end_date):
        return [e for e in self._earnings[symbol] if start_date <= e.event_date <= end_date]

    def subscribeFeed(self, instrument):
        if self.live:
            log.debug("Subscribing to: %s", instrument)
            #self._feed.subscribeRealtimeBars(instrument, useRTH_=False)
            #time.sleep(11)  # Need to sleep to ensure 60 req/10 minutes pace criteria
            self._feed.subscribeMarketBars(instrument)

    def unsubscribeFeed(self, instrument):
        if self.live:
            #self._feed.unsubscribeRealtimeBars(instrument)
            self._feed.unsubscribeMarketBars(instrument)

    def addCSVWriter(self, instr):
        if self.live:
            year = datetime.datetime.now().year
            filename = "%s/HC-%s-1M-%s-ib%s.csv" % (CSV_CACHE_DIR, instr, year, self.tag)
            log.debug("Recording bars to: %s", filename)
            try:
                self.csv_writer[instr] = BarsToCSV(filename, append=True, frequency=Frequency.MINUTE,
                               columns=['Date Time', 'Open', 'High', 'Low', 'Close', 'Volume'],
                               delimiter=',')
            except Exception as e:
                log.error("Exception during instantiating writer: %s" % e, exc_info=e)

    def writeBarToCSV(self, instr, bar):
        if self.live:
            if instr in self.csv_writer and self.csv_writer[instr]:
                try:
                    bars = [bar, ]  # List with one element :S
                    self.csv_writer[instr].writeBars(bars)
                    self.csv_writer[instr].flush()
                except Exception as e:
                    log.error("Exception during writing to csv: %s" % e, exc_info=e)


    def _createStrategy(self, now):
        """(re)Create the StatArbStrategy for each pair defined"""
        for pair in self.pairs:
            # We create one position per pair and map that
            # StatArbStrategy to both of the instruments
            if self._positions[pair[0]] is not None:
                # Stop if it was running
                self._positions[pair[0]].stop_Guarded()

            # Create a new instance
            statArb = StatArbStrategy(pair, self._statArbConfig[pair], now, self)

            # Assign the StatArbStrategy instance to both instruments
            # This ensures that the _onBars() can quickly dispatch the bars.
            # If we would register the StatArbStrategy as pair, we would need to
            # search for the instrument in the pair list in the _onBars.
            self._positions[pair[0]] = statArb
            self._positions[pair[1]] = statArb

    def _onDayStart(self, now):
        """Called at the beginning of every day"""
        # Record  statistics
        equity = self.broker.getEquity()
        leverage = self.broker.getLeverage()

        # Save to CSV the daily equity value
        if self.live:
            dt = datetime.datetime.now().strftime(DT_FMT)
            logEquityToCSV(self.tag, dt, equity)
        else:
            self._analyzer.addDailyEquity(equity)
            self._plotter.addEquityDS(self.today, equity)

        log.info('<[:]> What a beautiful new day. Net liquidation: %.2f, leverage: %.2f', equity, leverage)

        if equity <= 0:
            log.info("Game over! Net liquidation: %.2f", equity)
            self.stop()

        # Update RiskManager with the actual equity
        self.riskManager.setTradeCapital(equity)

        # Re-create strategies
        self._createStrategy(now)

    def _onDayEnd(self):
        """Called at the end of each day in live trading."""
        # After RTH in live trading, stop all StatArbPositions
        equity = self.broker.getEquity()
        leverage = self.broker.getLeverage()
        log.info("<[:]> After hours, exiting. Net liquidation: %.2f, leverage: %.2f", equity, leverage)

        if self.live:
            for instr in self.csv_writer:
                if self.csv_writer[instr]:
                    self.csv_writer[instr].close()
                    self.csv_writer[instr] = None

            dt = datetime.datetime.now().strftime(DT_FMT)
            logEquityToCSV(self.tag, dt, equity)

            self.stop()

        for pair in self.pairs:
            self._positions[pair[0]].stop_Guarded()

    def _onEveryHour(self, now):
        dtStr = now.strftime(DT_FMT)
        equity = self.broker.getEquity()
        leverage = self.broker.getLeverage()
        self.riskManager.setTradeCapital(equity)
        log.info("%s Net Liquidation: %.2f, leverage: %.2f", dtStr, equity, leverage)

    def _onBars(self, bars):
        for instr in bars.getInstruments():
            self.writeBarToCSV(instr, bars.getBar(instr))

        # We need to re-create the strategy every day. This is only useful in backtesting.
        # In live operation the application (therefore the BrokerAgent) is started once every day,
        # while in backtesting the BrokerAgent is created only once. To have the same behavior in
        # live and backtesting we manually re-create the StatArbStrategy positions if the day changes.
        barDT = bars.getDateTime().astimezone(self.EasternTZ)
        barDate = barDT.date()
        barTime = barDT.time()

        if self.RTHStart <= barTime <= self.RTHEnd:
            # Beginning of the day task
            if barDate != self.today:
                self.today = barDate
                self._currentHour = barTime.hour
                self._onDayStart(now=barDT)

            # Hourly task
            if barTime.hour > self._currentHour:
                self._currentHour = barTime.hour
                self._onEveryHour(barDT)

            # Analyzers are used only in backtest & optimization
            if not self.live:
                self._analyzer.notifyAnalyzers(lambda s: s.beforeOnBars(self))

            # Dispatch bars to StatArbStrategy's onBars
            for instrument in bars.getInstruments():
                if instrument in self._positions:
                    self._positions[instrument].onBars_Guarded(bars.getBar(instrument), instrument)

            # Plotter is used only in backtest & optimization
            if not self.live:
                self._plotter.getBarsProcessedEvent().emit(self, bars)

            if barTime == self.RTHEnd:
                self._onDayEnd()

            self.processed_bars += 1
        elif self.RTHEnd < barTime:
            # End of the day task
            self._onDayEnd()
        elif not self.live:
            log.warning("Bar is outside RTH, skipping: %s", barDT)

    # Taken from pyalgotrade/strategy.py, modified to work with orders
    def _onOrderUpdate(self, broker_, order):
        instrument = order.getInstrument()

        # Notify the SpecPosition
        if instrument in self._positions:
            self._positions[instrument].onOrderUpdate_Guarded(order)
        else:
            log.warning("_onOrderUpdate is ignoring %s order update", instrument)

    # Taken from pyalgotrade/strategy.py
    def run(self):
        """Call once (**and only once**) to backtest the strategy. """
        self._feed.getNewBarsEvent().subscribe(self._onBars)
        self._feed.start()
        self.broker.start()

        # Dispatch events as long as the feed or the broker have something to dispatch.
        stopDispBroker = self.broker.stopDispatching()
        stopDispFeed = self._feed.stopDispatching()
        while not stopDispFeed or not stopDispBroker:
            if not stopDispBroker:
                self.broker.dispatch()
                # self.btBroker.dispatch()
            if not stopDispFeed:
                self._feed.dispatch()
            stopDispBroker = self.broker.stopDispatching()
            stopDispFeed = self._feed.stopDispatching()

            if self.live:
                # Live trading is not driven by dispatch. We can save cpu cycles by sleeping here
                sleep(0.1)

        if self._feed.getCurrentBars() is not None:
            pass
        else:
            log.warn("Feed was empty")

        self.stop()

    # Taken from pyalgotrade/strategy.py
    def stop(self):
        if not self._stopped:
            log.info("Stopping...")

            for pair in self.pairs:
                if self._positions[pair[0]] is not None:
                    self._positions[pair[0]].stop_Guarded()  # Stop each StatArbPosition

            if not self.live:
                self._feed.getNewBarsEvent().unsubscribe(self._onBars)

            self.broker.stop()
            self._feed.stop()

            self.broker.join()
            self._feed.join()

            self._stopped = True
