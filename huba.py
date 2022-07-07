#!/usr/bin/env python
"""HUBA: Highly Unorthodox Broker Agent.
      Tibor Kiss <tibor.kiss@gmail.com> - Copyright (c) 2012-2014 All rights reserved

Usage:
  huba.py backtest [--strategy=S] [--from=START] [--to=END] [--freq=FREQ] (--paper|--real|--all|--file FILES...|--instr INSTRS...) [-oOqvdcpPmT] [-t TAG] [--proxy URL]
  huba.py live-trade (--paper|--real|--instr INSTRS...) [-qvdcT]
  huba.py -h | --help

Commands:
  backtest         Backtest a set of instruments in the given time frame with the given strategy
  live-trade       Live trading of the strategy

Options:
  --strategy=S     Strategy to use: StatArb, BuyAndHold [Default: StatArb]
  --from=START     Date of the start date of backtesting [Default: 20090101]
  --to=END         Date of the end date of backtesting [Default: 20141231]
  --freq=BAR_FREQ  Frequency (1D or 1M) of the bars used in backtesting [Default: 1M]
  --paper          Use the paper trading instruments either with backtest or with paper trading account
  --real           Use the real trading instruments either with backtest or with real trading account
  --all            Use all the registered instruments for backtest
  --proxy=URL      Use SOCKS proxy
  -o --optimize    Run the backtest with all the possible strategy parameter combinations
  -O --offline     Offline mode, do not download historical data
  -q --quiet       Reduce logging output
  -v --verbose     Increase logging output
  -d --debug       Show debug messages
  -c --console     Use ipython console
  -p --plot        Show plot of the backtest
  -P --saveplot    Save plot of the backtest
  -m --multicore   Multicore acceleration. Use all the available threads
  -t --tag=TAG     Tag for the run. The result and log files will contain the tag name
  -T --trace       Trace the program execution (set -x alike)
  -V --version     Show program version
  -h --help        Show this screen

"""

from tools import LOG_DIR, PYALGOTRADE_PATH
from tools import get_git_version
import sys
sys.path.append(PYALGOTRADE_PATH)

import os
import time, datetime

from urllib2 import HTTPError

import multiprocessing
from threading import Thread
import IPython

import logging
log = logging.getLogger(__name__)

from pyalgotrade.providers.interactivebrokers import ibconnection, ibfeed, ibbroker
from pyalgotrade.bar import Bar
from pyalgotrade.barfeed import Frequency
from pyalgotrade.stratanalyzer import returns, drawdown, trades
from pyalgotrade.utils.cache import memoize

from strategy.analyzer import calculateStats, printStats, saveResult, plotter
from strategy.brokeragent import BrokerAgent
from strategy.statarb_params import StatArbParams
from config import StatArbPairsParams, StatArbConfig, StatArbPairsParamsShared, generateStrategyParms
from tools import DT_FMT, IS_PYPY, attributesFromDict, LogFilter
from tools.docopt import docopt
from tools.csv_tools import loadHistoricalBars, expandDailyBars, EasternTZ
from tools.tracing import CallTracing
from tools.workdays import daterange


IPShellBanner = '\n>>> HUBA - Statistical Arbitrage. Useful vars: connection, broker, feed & brokerAgent'

HUBA_NEW_DAY_EVENT="HUBA_NEW_DAY_EVENT"

class Huba(object):
    def __init__(self, action, account, accountCode, twsConnStr, leverage, btStartDate, btEndDate, btBarFrequency,
                 tag, offline, optimize, displayPlot, savePlot, savePlotSharpeThresh, console):
        attributesFromDict(locals())

        # self._db_handler = DBHandler(HUBA_DB_URI)
        self._db_handler = None

    def _liveTrade(self, configs):
        # Live trading with IB
        live = True
        pairs = configs.keys()
        log.info("Going live with %d pairs: %s " % (len(pairs), pairs))

        # Connection to TWS
        twsHost, twsPort, twsClientId = self.twsConnStr.split(':')
        twsPort, twsClientId = int(twsPort), int(twsClientId)

        # Paper trading account works with flat rate commission
        if self.tag == 'real':
            commission = ibbroker.CostPlusCommission()
        else:
            commission = ibbroker.FlatRateCommission()

        connection = ibconnection.Connection(self.accountCode, twsHost, twsPort, twsClientId)

        beginning_of_day = datetime.datetime.now(tz=EasternTZ)
        new_day_bar = Bar(beginning_of_day, open_=None, high=None, low=None, close=None, volume=None, adjClose=None)
        feed = ibfeed.LiveFeed(connection, barsToInject=[{HUBA_NEW_DAY_EVENT: new_day_bar}])

        broker = ibbroker.Broker(feed, connection, commission)

        earnings_start_date = datetime.datetime.now() - datetime.timedelta(days=365)
        earnings_end_date = datetime.datetime.now() + datetime.timedelta(days=90)
        earnings = {}
        for pair in pairs:
            if self._db_handler:
                earnings[pair[0]] = self._db_handler.load_company_earnings(pair[0], earnings_start_date, earnings_end_date,
                                                                        True, True, True, True)
                earnings[pair[1]] = self._db_handler.load_company_earnings(pair[1], earnings_start_date, earnings_end_date,
                                                                        True, True, True, True)

        # Run the BrokerAgent in separate thread, IPython will run in the main thread
        brokerAgent = BrokerAgent(feed, broker, live, configs, earnings, self.leverage, self.tag, offline=False)
        thread = Thread(target=brokerAgent.run)
        thread.start()

        # Start IPython console
        if self.console:
            IPython.embed(header=IPShellBanner)

        # Wait for exit
        thread.join()

        return None

    @memoize(size=2, lru=True)
    def _loadHistoricalBars(self, instrument, startDate, endDate, freq, offline):
        """loadHistoricalBars wrapper to enable caching on the backtest feed.
           If csv_tools.loadCSV would have been cached then the daily bars used for z-score calculation
           would have been also cached. If mixed sized data is cached it is difficult to optimize the cache's
           size.
        """
        bars = loadHistoricalBars(instrument, startDate, endDate, freq, offline=offline)
        return bars

    def _loadBacktestFeed(self, feed, pair):
        """Returns dayCount and barCount with the pairs between start and end date"""
        dayCount = 0
        barCount = 0

        bars = {}
        try:
            for instr in pair:
                # Expand the daily OHLC bar into 4 bars
                bars[('1D', instr)] = expandDailyBars(self._loadHistoricalBars(instr, self.btStartDate, self.btEndDate,
                                                    Frequency.DAY, self.offline))

            if self.btBarFrequency == '1M':
                for instr in pair:
                    bars[('1M', instr)] = self._loadHistoricalBars(instr, self.btStartDate, self.btEndDate,
                                                                   Frequency.MINUTE, self.offline)
        except HTTPError as e:
            log.error('Unable to download historical bars from yahoo: %s', e)
            return dayCount, barCount

        for bars_key in bars:
            freq, instr = bars_key

            if self.btBarFrequency == freq:
                feed.addBarsFromSequence(instr, bars[bars_key])

        # Find the first and last timestamp
        first_bar_timestamp = EasternTZ.localize(datetime.datetime(2420, 12, 31))
        for bar in bars:
            first_bar_timestamp = min(first_bar_timestamp, bars[bar][0].getDateTime())

        last_bar_timestamp = EasternTZ.localize(datetime.datetime(1970, 1, 1))
        for bar in bars:
            last_bar_timestamp = max(last_bar_timestamp, bars[bar][-1].getDateTime())

        # Add New Day Event 'Bars' which are used to trigger onNewDay
        new_day_bars = []
        for date_ in daterange(first_bar_timestamp, last_bar_timestamp):
            beginning_of_day = datetime.datetime(date_.year, date_.month, date_.day, 9, 30, 0, 0, tzinfo=EasternTZ)
            new_day_bar = Bar(beginning_of_day,
                              open_=None, high=None, low=None, close=None, volume=None, adjClose=None)
            new_day_bars.append(new_day_bar)
        feed.addBarsFromSequence(HUBA_NEW_DAY_EVENT, new_day_bars)

        days = set()
        for bars_key in bars:
            for bar in bars[bars_key]:
                days.add(bar.getDate())
                barCount = max(barCount, len(bars[bars_key]))  # TODO: this is not really correct...

        dayCount = len(days)

        return dayCount, barCount

    def _backtest(self, configs):
        pairs = configs.keys()
        log.info("Backtest %s - %s for pairs: %s" % (self.btStartDate, self.btEndDate, pairs))
        backtest_start = datetime.datetime.now()

        live = False
        leverage = 1.0

        # Load backtest feed
        feed = ibfeed.CSVFeed()
        dayCount = 0
        barCount = 0
        for pair in pairs:
            dc, bc = self._loadBacktestFeed(feed, pair)
            dayCount += dc
            barCount += bc
        dayCount /= len(pairs)
        barCount /= len(pairs)

        # BrokerAgent will create the backtesting broker
        broker = None

        earnings = {}
        for pair in pairs:
            if self._db_handler:
                earnings[pair[0]] = self._db_handler.load_company_earnings(pair[0], self.btStartDate, self.btEndDate,
                                                                        True, True, True, True)
                earnings[pair[1]] = self._db_handler.load_company_earnings(pair[1], self.btStartDate, self.btEndDate,
                                                                        True, True, True, True)

        # Create BrokerAgent
        brokerAgent = BrokerAgent(feed, broker, live, configs, earnings, leverage, self.tag, self.offline)

        # Create strategy analyzers
        retAnalyzer = returns.Returns()
        drawDownAnalyzer = drawdown.DrawDown()
        tradesAnalyzer = trades.Trades()

        # Attach analyzers
        for analyzer in (retAnalyzer, drawDownAnalyzer, tradesAnalyzer):
            brokerAgent._analyzer.attachAnalyzer(analyzer)

        # Start the BrokerAgent
        brokerAgent.run()

        # Display and save the results
        stats = calculateStats(brokerAgent, self.btStartDate, self.btEndDate, dayCount, barCount,
                               retAnalyzer, drawDownAnalyzer, tradesAnalyzer)
        printStats(pairs, self.btStartDate, self.btEndDate, configs, stats)
        saveResult('backtest', pairs, self.btStartDate, self.btEndDate, self.btBarFrequency, stats,
                   configs, self.tag)

        backtest_run_length = datetime.datetime.now() - backtest_start
        bars_per_sec = float(brokerAgent.processed_bars) / float(backtest_run_length.total_seconds())
        log.critical("%s - Performance: %.2f bars / sec", pairs, bars_per_sec)

        # IPython console
        if self.console:
            IPython.embed(header=IPShellBanner)

        # Show plotter if enabled, use Sharpe threshold for saving images if set to float
        if not IS_PYPY and self.displayPlot or self.savePlot and self.savePlotSharpeThresh <= stats['sharpe']:
            plotter(brokerAgent, self.btStartDate, self.btEndDate, self.btBarFrequency, stats, configs, self.displayPlot,
                    self.savePlot, self.tag)

        return stats

    def run(self, pairs, parms=None):
        configs = {}
        for pair in pairs:
            if pair in StatArbPairsParams[self.account]:
                cfg = StatArbPairsParams[self.account][pair]
                log.info("Configuration loaded for %s: %s", pair, cfg)
            else:
                cfg = StatArbParams()
                log.info("Default configuration loaded for %s: %s", pair, cfg)
            configs[pair] = cfg

        if self.tag != '':
            log.info('Tag: %s' % self.tag)

        if self.action == 'live-trade':
            # Live trading
            self._liveTrade(configs)
        elif self.action == 'backtest':
            # Backtest one configuration
            if not self.optimize:
                results = self._backtest(configs)
                return results
            else:
                # Backtest all the possible configurations
                strategyParmsIter = generateStrategyParms(pairs, self.leverage, self.tag)
                for _, _, statArbParams, _, _ in strategyParmsIter:
                    self._backtest(statArbParams)  # Do not store & return the results
        else:
            raise Exception("Invalid action: %s" % self.action)


    def __call__(self, pairs, parms=None):
        # Use this function with multiprocessing, it sets the tag based on the thread
        # and calls Huba.run()

        # include process name in tag to avoid backtest.csv concurrency in multicore runs
        process_name = multiprocessing.current_process().name
        if process_name != 'MainProcess' and self.tag.find(process_name) == -1:
            self.tag = "%s-%s" % (self.tag, process_name)

        try:
            # Do not return the results: This function is used with multiprocessing
            # and the final results will be evaluated from the csv results files
            log.critical("Processing %s: %s", process_name, pairs)
            self.run(pairs, parms)
        except Exception as e:
            log.error("Exception with pair %s: %s" % (pairs, str(e)), exc_info=e)


def setup_logging(tag, args):
    # Logger parameters
    LOGFMT='%(asctime)s [%(levelname).1s] %(module)12s %(message)s'
    action = '' if args['live-trade'] else '-backtest'
    logfile = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "%s/huba%s%s-%s.log" %
                         (LOG_DIR, action, tag, datetime.datetime.now().strftime("%Y%m%d")))
    logFormatter = logging.Formatter(fmt=LOGFMT, datefmt=DT_FMT)

    # Console and file handlers
    logFile = logging.FileHandler(filename=logfile, mode='a+')
    logFile.setFormatter(logFormatter)
    logConsole = logging.StreamHandler(sys.stdout)
    logConsole.setFormatter(logFormatter)

    # Start logging
    if multiprocessing.current_process().name == "MainProcess":
        log = logging.getLogger()
    else:
        log = multiprocessing.get_logger()
    log.addHandler(logConsole)
    log.addHandler(logFile)

    # Quiet by default
    log.setLevel(logging.INFO)
    logConsole.setLevel(logging.INFO)
    logFile.setLevel(logging.INFO)
    logging.getLogger("strategy.statarb").setLevel(logging.WARNING)
    logging.getLogger("strategy.brokeragent").setLevel(logging.WARNING)
    logging.getLogger("tools.perfmon").setLevel(logging.INFO)

    if args['--quiet']:
        log.setLevel(logging.ERROR)
        logging.getLogger("strategy.statarb").setLevel(logging.ERROR)
        logging.getLogger("strategy.brokeragent").setLevel(logging.ERROR)

    if args['--verbose']:
        log.setLevel(logging.DEBUG)
        logConsole.setLevel(logging.INFO)
        if args['live-trade']:
            logFile.setLevel(logging.DEBUG)
        else:
            logFile.setLevel(logging.INFO)
        logging.getLogger("strategy.statarb").setLevel(logging.DEBUG)
        logging.getLogger("strategy.brokeragent").setLevel(logging.DEBUG)
        logging.getLogger("tools.earnings").setLevel(logging.DEBUG)
        logging.getLogger("pyalgotrade.providers.interactivebrokers").setLevel(logging.DEBUG)

    if args['--debug']:
        log.setLevel(logging.DEBUG)
        logConsole.setLevel(logging.DEBUG)
        logFile.setLevel(logging.DEBUG)
        logging.getLogger("strategy.statarb").setLevel(logging.DEBUG)
        logging.getLogger("strategy.brokeragent").setLevel(logging.DEBUG)
        logging.getLogger("pyalgotrade.providers.interactivebrokers").setLevel(logging.DEBUG)

        log.debug("Cmd line args: %s " % args)

    if args['--trace']:
        tracing = CallTracing(patternsToTrace=["strategy"])
        tracing.start()

    return log, logConsole, logFile


def load_pairs(args):
    # Create and return list of tuples of pair tuples
    # Each element in this list is a run and each run
    # contains one or more pairs of instruments
    # The strings of the symbols are intern()'ed in order to save space.
    pairs = []
    if args['--file']:
        # Load pairs from file

        # Filter 'Invalid share quantites' and 'RiskManager refused to register' messages from StatArb
        # and  'Exception with pair (('STT', 'AGII'),): [Errno 2] No such file or directory:' from Huba
        logging.getLogger('strategy.statarb').addFilter(LogFilter('Invalid share quantities'))
        logging.getLogger('strategy.statarb').addFilter(LogFilter('RiskManager refused to register'))
        logging.getLogger('').addFilter(LogFilter('No such file or directory'))

        # Load the pairs from the file
        for filename in args['FILES']:
            with open(filename, 'r') as f:
                for pair in f:
                    p = pair.strip().split('_')
                    p = (intern(p[0].upper()), intern(p[1].upper()))  # Pair tuple
                    pairs.append((p,))  # Append tuple of pairs

    if args['--real']:
        # Load all pairs from config
        for pair in StatArbConfig['Real']['Pairs']:
            p = pair.strip().split('_')
            p = (intern(p[0].upper()), intern(p[1].upper()))  # Pair tuple
            pairs.append((p,))  # Append tuple of pairs

    if args['--paper']:
        # Load all pairs from config
        for pair in StatArbConfig['Paper']['Pairs']:
            p = pair.strip().split('_')
            p = (intern(p[0].upper()), intern(p[1].upper()))  # Pair tuple
            pairs.append((p,))  # Append tuple of pairs

    if args['--all']:
        # Load all pairs from StatArbPairsParamsShared
        for pair in StatArbPairsParamsShared.keys():
            pairs.append((pair, ))

    instruments = args['--instr']  # List of strings
    if instruments:
        # Parse pairs from argument list (for backtesting)
        # One run with all the provided pairs
        p2 = []
        for pair in args['INSTRS']:
            p = pair.strip().split('_')
            p = (intern(p[0].upper()), intern(p[1].upper()))  # Pair tuple
            p2.append(p)  # Append tuple of pairs
        pairs.append(p2)

    return pairs

def flatten_pairs(pairs):
    """In case of live trading flatten the pair list.
    """
    p = (list(), )

    for p1 in pairs:
        for p2 in p1:
            p[0].append(p2)

    return p


def main(args):
    # Parse command line args
    args = docopt(__doc__, argv=args, version=get_git_version())

    # Action to take: live trading or backtest
    action = 'live-trade' if args['live-trade'] else 'backtest'

    # Tag
    if action == 'backtest':
        if not args['--tag']:
            tag = ''
        else:
            tag = '-%s' % args['--tag']
    else:
        if args['--real']:
            tag = '-real'
        if args['--paper']:
            tag = '-paper'
        if args['--all']:
            tag = '-all'
        if args['--instr']:
            tag = '-test'

    log, logConsole, logFile = setup_logging(tag, args)


    if args['--multicore']:
        # Create process pool before the pairs are loaded
        # This way the children will not inherit the possibly
        # large pairs datastructure
        pool = multiprocessing.Pool()

    # Load the pairs from command line and input file
    pairs = load_pairs(args)

    if action == 'backtest':
        account = 'Real'
    elif action == 'live-trade':
        if args['--real']:
            account = 'Real'
        elif args['--paper']:
            account = 'Paper'
        elif args['--instr']:
            account = 'Test'
        else:
            log.error("Invalid instrument list for live-trade")
            sys.exit(1)

        # Flatten the loaded pairs
        pairs = flatten_pairs(pairs)
    else:
        log.error("Invalid action: %s" % action)
        return

    accountCode = StatArbConfig[account]['AccountCode']
    twsConnStr = StatArbConfig[account]['TWSConnection']
    leverage = StatArbConfig[account]['Leverage']

    if args['--proxy']:
        import tools.socks as socks
        import socket

        proxy_host, proxy_port = args['--proxy'].split(':')
        proxy_port = int(proxy_port)

        log.info('Using SOCKS Proxy: %s:%d' % (proxy_host, proxy_port))
        socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, proxy_host, proxy_port)
        socket.socket = socks.socksocket

    offline = args['--offline']
    optimize = args['--optimize']
    displayPlot = args['--plot']
    savePlot = args['--saveplot']
    console = args['--console']

    # Backtest dates
    btStartDate = datetime.datetime.strptime(args['--from'], "%Y%m%d").date()
    btEndDate = datetime.datetime.strptime(args['--to'], "%Y%m%d").date()
    btBarFreq = args['--freq']
    if btBarFreq not in ('1M', '1D'):
        log.error("Backtest bar frequency is invalid: %s" % args.bt_bar_size)
        return

    log.info("Version: %s" % get_git_version())

    # Count the number of possible parameters if optimization is enabled
    run_per_iter = len([e for e in generateStrategyParms('x')]) if optimize else 1
    run_cnt = len(pairs) * run_per_iter
    log.critical("Created %d runs", run_cnt)

    huba = Huba(action=action, account=account, accountCode=accountCode, twsConnStr=twsConnStr, leverage=leverage,
                btStartDate=btStartDate, btEndDate=btEndDate, btBarFrequency=btBarFreq,
                tag=tag, offline=offline, optimize=optimize,
                displayPlot=displayPlot, savePlot=savePlot, savePlotSharpeThresh=None, console=console)

    results = []
    if args['--multicore']:
        rs = pool.map_async(huba, pairs)
        pool.close()

        try:
            while not rs.ready():
                time.sleep(60)
        except KeyboardInterrupt:
            pool.terminate()
        else:
            pool.join()
            # results = rs.get()
        finally:
            pass
    else:
        for i, pair in enumerate(pairs):
            try:
                result = huba.run(pair)
                results.append(result)
            except Exception as e:
                log.error("Exception with pair %s: %s" % (pairs, str(e)), exc_info=e)

                if type(e) == ibconnection.IBConnectionException:
                    raise

    log.removeHandler(logConsole)
    log.removeHandler(logFile)

    return results

if __name__ == '__main__':
    main(sys.argv[1:])
