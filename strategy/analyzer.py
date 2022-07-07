
from tools import LOG_DIR

import datetime
from collections import OrderedDict

import logging
log = logging.getLogger(__name__)

from pyalgotrade.broker import Order
from pyalgotrade import observer
from pyalgotrade import dataseries
from pyalgotrade.barfeed import Frequency
from pyalgotrade.stratanalyzer.sharpe import sharpe_ratio_2
from pyalgotrade.stratanalyzer.sortino import sortino_ratio

from tools import IS_PYPY, get_git_version
from tools.csv_tools import loadHistoricalBars

if not IS_PYPY:
    from matplotlib import pyplot as plt
    from matplotlib.ticker import FuncFormatter
    import numpy as np


from tools.csv_tools import logResultsToCSV


class AnalyzerResult:
    def __init__(self, pairs, startDate, endDate, dayCount, yearCount,
                 strategyConfig, finalPortfolioValue, cumulativeReturn,
                 CAGR, sharpeRatio, maxDrawDownPct, drawDownDuration,
                 totalNrOfTrades, profitableTrades, unprofitableTrades, avgProfit):
        self.pairs = None
        self.startDate = None
        self.endDate = None


class Analyzer(object):
    def __init__(self, broker):
        self._broker = broker

        # For strategy analyzer
        self.__analyzers = []
        self.__namedAnalyzers = {}

        # Statistics
        self._dailyEquities = []  # For Sharpe & Sortino calculation
        self._dailyReturns = None

    def _calcDailyReturns(self):
        self._dailyReturns = []
        for i, equity in enumerate(self._dailyEquities):
            if i > 1:
                ret = (self._dailyEquities[i] - self._dailyEquities[i-1])/float(self._dailyEquities[i-1])
                self._dailyReturns.append(ret)

    def addDailyEquity(self, equity):
        self._dailyEquities.append(equity)

    def getDailyReturns(self):
        if self._dailyReturns is None:
            self._calcDailyReturns()

        return self._dailyReturns

    def getSharpe(self, firstDateTime, lastDateTime):
        if self._dailyReturns is None:
            self._calcDailyReturns()
        return sharpe_ratio_2(self._dailyReturns, 0.05, firstDateTime, lastDateTime)

    def getSortino(self):
        if self._dailyReturns is None:
            self._calcDailyReturns()
        return sortino_ratio(self._dailyReturns)

    def getBroker(self):
        return self._broker

    # Taken from pyalgotrade/strategy.py
    def notifyAnalyzers(self, lambdaExpression):
        for s in self.__analyzers:
            lambdaExpression(s)

    # Taken from pyalgotrade/strategy.py
    def attachAnalyzerEx(self, strategyAnalyzer, name=None):
        if strategyAnalyzer not in self.__analyzers:
            if name != None:
                if name in self.__namedAnalyzers:
                    raise Exception("A different analyzer named '%s' was already attached" % name)
                self.__namedAnalyzers[name] = strategyAnalyzer

            strategyAnalyzer.beforeAttach(self)
            self.__analyzers.append(strategyAnalyzer)
            strategyAnalyzer.attached(self)

    # Taken from pyalgotrade/strategy.py
    def attachAnalyzer(self, strategyAnalyzer):
        """Adds a :class:`pyalgotrade.stratanalyzer.StrategyAnalyzer`."""
        self.attachAnalyzerEx(strategyAnalyzer)

    # Taken from pyalgotrade/strategy.py
    def getNamedAnalyzer(self, name):
        return self.__namedAnalyzers.get(name, None)


class Plotter(object):
    def __init__(self, pairs):
        self.barsProcessedEvent = observer.Event()

        self._plots = {}

        # Plots - one for each pair
        self._priceDS = {}  # Close price
        self._buyDS = {}    # Buy/Sell Signals
        self._sellDS = {}
        self._zScoreDS = {}
        self._spread = {}
        self._spreadMean = {}
        self._spreadStd = {}

        # Store the Z-Score per pair
        for pair in pairs:
            self._zScoreDS[pair] = dataseries.SequenceDataSeries()

            # Store price and buy/sell signals for both instruments in each pair
            for instrument in pair:
                self._priceDS[instrument] = dataseries.SequenceDataSeries()
                self._buyDS[instrument] = dataseries.SequenceDataSeries()
                self._sellDS[instrument] = dataseries.SequenceDataSeries()

        # Portfolio/Equity per time
        self._equityDS = dataseries.SequenceDataSeries()

    def getBarsProcessedEvent(self):
        return self.barsProcessedEvent

    def addDataPoint(self, plotName, dateTime, value):
        plot = self._plots.setdefault(plotName, dataseries.SequenceDataSeries())
        plot.appendValueWithDatetime(dateTime, value)

    def getPlot(self, plotName):
        return self._plots[plotName]

    def getSeries(self, plotName):
        return {'x': self._plots[plotName].getDateTimes(),
                'y': self._plots[plotName]}

    def addEquityDS(self, dateTime, equity):
        self._equityDS.appendValueWithDatetime(dateTime, equity)

    def getEquityCoords(self):
        return {'x': self._equityDS.getDateTimes(),
                'y': self._equityDS }

    def addPriceDS(self, instrument, dateTime, price):
        self._priceDS[instrument].appendValueWithDatetime(dateTime, price)

    def getPriceCoords(self, instrument):
        return {'x': self._priceDS[instrument].getDateTimes(),
                'y': self._priceDS[instrument]}

    def addBuySellDS(self, instrument, dateTime, price, action):
        if action in (Order.Action.BUY, Order.Action.BUY_TO_COVER):
            self._buyDS[instrument].appendValueWithDatetime(dateTime, price)
        elif action in (Order.Action.SELL, Order.Action.SELL_SHORT):
            self._sellDS[instrument].appendValueWithDatetime(dateTime, price)
        else:
            raise Exception("Invalid order type!")

    def getBuyCoords(self, instrument):
        return {'x': self._buyDS[instrument].getDateTimes(),
                'y': self._buyDS[instrument]}

    def getSellCoords(self, instrument):
        return {'x': self._sellDS[instrument].getDateTimes(),
                'y': self._sellDS[instrument]}

    def addZScoreDS(self, pair, dateTime, zScore):
        self._zScoreDS[pair].appendValueWithDatetime(dateTime, zScore)

    def getZScoreCoords(self, pair):
        return {'x': self._zScoreDS[pair].getDateTimes(),
                'y': self._zScoreDS[pair]}

    # Taken from pyalgotrade/strategy.py
    def getBarsProcessedEvent(self):
        return self.barsProcessedEvent


def calculateStats(brokerAgent, startDate, endDate, dayCount, barCount, retAnalyzer, drawDownAnalyzer, tradesAnalyzer):
    beginningNAV = brokerAgent.initialEquity
    endingNAV = brokerAgent.getEquity()
    cumReturn = 0
    CAGR = 0
    sharpe = -100
    sortino = -111
    maxDrawDown = 0
    drawDownDays = 0
    dayPerBar = 0
    totalTrades = 0
    profitableTrades = 0
    unprofitableTrades = 0
    avgProfit = 0

    yearCount = dayCount / float(252)
    if barCount != 0:
        cumReturn = retAnalyzer.getCumulativeReturns()[-1] * 100
        cumReturn = -100 if cumReturn < -100 else cumReturn  # Case of bankruptcy
        if endingNAV < 0:
            CAGR = -100
        else:
            CAGR = (((endingNAV / beginningNAV) ** (1 / yearCount)) -1) * 100
        dayPerBar = dayCount / float(barCount)

        sharpe = brokerAgent._analyzer.getSharpe(startDate, endDate)
        sortino = brokerAgent._analyzer.getSortino()
        maxDrawDown = drawDownAnalyzer.getMaxDrawDown() * 100
        drawDownDays = drawDownAnalyzer.getLongestDrawDownDuration() * dayPerBar

        totalTrades = tradesAnalyzer.getCount()
        if totalTrades > 0:
            profitableTrades = tradesAnalyzer.getProfitableCount()
            unprofitableTrades = tradesAnalyzer.getUnprofitableCount()
            avgProfit = tradesAnalyzer.getAll().mean()

    dailyReturns = brokerAgent._analyzer.getDailyReturns()

    stats = {'barCount': barCount,
             'dayCount': dayCount,
             'yearCount': yearCount,
             'dayPerBar': dayPerBar,
             'finalPortfolio': brokerAgent.getEquity(),
             'cumReturn': cumReturn,
             'CAGR': CAGR,
             'sharpe': sharpe,
             'sortino': sortino,
             'maxDrawDown': maxDrawDown,
             'drawDownDays': drawDownDays,
             'totalTrades': totalTrades,
             'profitableTrades': profitableTrades,
             'unprofitableTrades': unprofitableTrades,
             'avgProfit': avgProfit,
             'dailyReturns': dailyReturns}

    return stats


def printStats(pairs, startDate, endDate, strategyConfig, stats):
    log.info("%s %s - %s (%d days or %.2f years, %d bars)",
             pairs, startDate, endDate, stats['dayCount'], stats['yearCount'], stats['barCount'])
    log.info("Strategy config: %s", strategyConfig)
    log.info("Final portfolio value: $%.2f", stats['finalPortfolio'])
    log.info("Cumulative returns: %.2f %%", stats['cumReturn'])
    log.info("CAGR: %.2f %%", stats['CAGR'])
    log.info("Sortino: %.2f", stats['sortino'])
    log.info("Sharpe ratio: %.2f", stats['sharpe'])
    log.info("Max. drawdown: %.2f %%", stats['maxDrawDown'])
    log.info("Longest drawdown duration: %d days", stats['drawDownDays'])

    log.info("")
    log.info("Total trades: %d", stats['totalTrades'])
    log.info("Avg. profit: $%2.f", stats['avgProfit'])
    log.info("Profitable trades: %d", stats['profitableTrades'])
    log.info("Unprofitable trades: %d", stats['unprofitableTrades'])
    log.info("")


def saveResult(action, pairs, startDate, endDate, barFrequency, stats, strategyConfig, tag=''):
    currDT = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    od = OrderedDict()

    strategyParms = strategyConfig[pairs[0]]
    pairStr = ",".join(["_".join(e) for e in pairs])

    # Prepare the result dict
    od['BTDate'] = currDT
    od['Version'] = get_git_version()
    od['Pairs'] = pairStr
    od['StartDate'] = startDate
    od['EndDate'] = endDate
    od['BarFreq'] = barFrequency
    od['BarCount'] = stats['barCount']
    od['DayCount'] = stats['dayCount']
    od['Sharpe'] = '%.2f' % stats['sharpe']
    od['Sortino'] = '%.2f' % stats['sortino']
    od['CAGR'] = '%.2f' % stats['CAGR']
    od['CumRet'] = '%.2f' % stats['cumReturn']
    od['MaxDD'] = '%.2f' % stats['maxDrawDown']
    od['DDDur'] = '%d' % stats['drawDownDays']
    od['TotalTrades'] = '%d' % stats['totalTrades']
    od['ProfitableTrades'] = '%d' % stats['profitableTrades']
    od['UnprofitableTrades'] = '%d' % stats['unprofitableTrades']
    od['StrategyParams'] = strategyParms

    filename = '%s/%s%s.csv' % (LOG_DIR, action, tag)
    logResultsToCSV(filename, od)


def plotter(brokerAgent, startDate, endDate, barFrequency, stats, strategyConfig, displayPlot, savePlot, tag):
    if IS_PYPY or (not displayPlot and not savePlot):
        return

    pairs = brokerAgent.pairs

    # Create 2x2 plot grid
    fig, axes = plt.subplots(2, 2)

    fig.set_size_inches((18, 12))

    # Subplot 1: Show portfolio, with sharpe, max dd
    # Add SPY as reference
    spyBars = loadHistoricalBars('SPY', startDate, endDate, Frequency.DAY)
    spyStartPrice = spyBars[0].getAdjClose()
    spy = {'x': [e.getDateTime() for e in spyBars],
           'y': [100 * ((e.getAdjClose() - spyStartPrice) / spyStartPrice) for e in spyBars]}
    axes[0, 0].plot(spy['x'], spy['y'], label='Return % of SPY', color='red')

    # Add the portfolio
    portfolio = brokerAgent._plotter.getEquityCoords()
    portfolioStartPrice = portfolio['y'][0]
    portfolio['y'] = [100 * ((e - portfolioStartPrice) / portfolioStartPrice) for e in portfolio['y']]

    axes[0, 0].plot(portfolio['x'], portfolio['y'], label='Strategy', color='blue')
    axes[0, 0].fill_between(portfolio['x'], portfolio['y'], 0, facecolor='blue', alpha=0.3)
    axes[0, 0].set_title('%s-%s: Return %% of %s' % (startDate, endDate, pairs))
    axes[0, 0].yaxis.set_major_formatter(FuncFormatter(lambda a,b: '%s%%' % a))
    axes[0, 0].tick_params(labelright=True)
    axes[0, 0].legend(loc=2)


    # Subplot 2: Daily returns histogram
    # Convert the returns to percents and show them as histograms
    axes[0, 1].hist([e * 100 for e in stats['dailyReturns'] if e != 0],
                    bins=100, alpha=0.3, color='blue')
    axes[0, 1].set_title('Sortino: %.2f, Sharpe: %.2f, CAGR: %.2f%%, Cumm. return: %.2f%% Max DD: %.2f%%, DD Days: %d' %
                         (stats['sortino'], stats['sharpe'], stats['CAGR'], stats['cumReturn'], stats['maxDrawDown'],
                          stats['drawDownDays']))
    axes[0, 1].legend(('Daily Return %', ))
    axes[0, 1].xaxis.set_major_formatter(FuncFormatter(lambda a,b: '%s%%' % a))
    axes[0, 1].tick_params(labelright=True)

    # Per pair plots
    zScore = {}
    price = {}
    buy = {}
    sell = {}
    for pair in pairs:
        # Get the dataseries from the BrokerAgent
        zScore[pair] = brokerAgent._plotter.getZScoreCoords(pair)

        for instrument in pair:
            price[instrument] = brokerAgent._plotter.getPriceCoords(instrument)
            buy[instrument] = brokerAgent._plotter.getBuyCoords(instrument)
            sell[instrument] = brokerAgent._plotter.getSellCoords(instrument)

        # Subplot 2: Z-Score
        axes[1, 0].plot(zScore[pair]['x'], zScore[pair]['y'], color='black')
        axes[1, 0].set_title('%s' % str(strategyConfig[pair])[14:88])
        axes[1, 0].legend(('Z-Score',))
        axes[1, 0].set_ylim([-5, 5])
        axes[1, 0].tick_params(labelright=True)

        # Subplot 3: Stock prices and buy/sell signals, daily returns
        axes[1, 1].plot(price[pair[0]]['x'], price[pair[0]]['y'], color='pink')
        axes[1, 1].plot(price[pair[1]]['x'], price[pair[1]]['y'], color='orange')
        axes[1, 1].plot(buy[pair[0]]['x'], buy[pair[0]]['y'], 'g^')   # Buy signal: green up arrow
        axes[1, 1].plot(buy[pair[1]]['x'], buy[pair[1]]['y'], 'g^')
        axes[1, 1].plot(sell[pair[0]]['x'], sell[pair[0]]['y'], 'rv') # Sell signal: red down arrow
        axes[1, 1].plot(sell[pair[1]]['x'], sell[pair[1]]['y'], 'rv')
        axes[1, 1].set_title('Trades: %d, Profitable: %d, Unprofitable: %d, Avg Profit: %.2f' %
                            (stats['totalTrades'], stats['profitableTrades'], stats['unprofitableTrades'], stats['avgProfit']))
        axes[1, 1].set_ylim(bottom=0)
        axes[1, 1].legend((pair[0], pair[1]), loc='best')
        axes[1, 1].tick_params(labelright=True)

    if savePlot:
        currDT = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        pairStr = ""
        for pair in pairs:
            if pairStr == "":
                pairStr = "%s_%s" % (pair[0], pair[1])
            else:
                pairStr += ",%s_%s" % (pair[0], pair[1])
        filename = '%s/pics/%s-%s-%s-%s-%s.png' % (LOG_DIR, currDT, pairStr, startDate, endDate, tag)
        plt.savefig(filename)
        log.info("Plot saved as %s", filename)

    if displayPlot:
        plt.show()



