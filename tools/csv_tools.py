import csv, os, datetime, pytz

import logging
log = logging.getLogger(__name__)

from collections import OrderedDict
from copy import deepcopy

from pyalgotrade.bar import Bar
from pyalgotrade.barfeed import Frequency
from pyalgotrade.barfeed.iqfeed import RowParser as IQRowParser
from pyalgotrade.barfeed.yahoofeed import RowParser as YHRowParser
from pyalgotrade.utils import intersect
from pyalgotrade.utils.cache import memoize
from tools import iqfeed, yahoofinance, googlefinance
from tools import CSV_CACHE_DIR, LOG_DIR, retry

# NYSE
EasternTZ = pytz.timezone('US/Eastern')

class BarsToCSV(object):
    def __init__(self, filename, append, frequency, columns, delimiter):
        self.filename = filename
        self.append = append
        self.columns = columns
        self.delimiter = delimiter
        self.frequency = frequency

        if frequency == Frequency.MINUTE:
            self.dtFmt = "%Y%m%d %H%M%S"
        else:
            self.dtFmt = "%Y-%m-%d"

        self.fd = None
        fileExists = os.path.exists(filename)

        if filename.endswith('.gz'):
            if append:
                raise Exception("Unable to append to .gz file")

            self.fd = os.popen("gzip > %s" % filename, "w")
        else:
            opMode = "a" if append else "w"
            self.fd = open(filename, opMode)

            if append:
                self.fd.seek(0, 2)  # Seek to the end

        self.dw = csv.DictWriter(self.fd, columns, extrasaction='ignore', delimiter=delimiter)
        if not append or not fileExists:
            self.dw.writeheader()

    def writeBars(self, bars):
        # Convert list of Bar instances to list of Dict instances
        rows = [{self.columns[0]:  bar.getDateTime().astimezone(EasternTZ).strftime(self.dtFmt),
                 'Open':	  bar.getOpen(),
                 'High':	  bar.getHigh(),
                 'Low':	      bar.getLow(),
                 'Close':	  bar.getClose(),
                 'Adj Close': bar.getAdjClose(),
                 'Volume':	  bar.getVolume(),
                 } for bar in bars]

        for row in rows:
            self.dw.writerow(row)

    def flush(self):
        self.fd.flush()

    def close(self):
        self.fd.close()


def writeBarsToNTCSV(bars, filename, append):
    writer = BarsToCSV(filename, append, frequency=Frequency.MINUTE,
                       columns=['Date Time', 'Open', 'High', 'Low', 'Close', 'Volume'],
                       delimiter=',')
    writer.writeBars(bars)
    writer.close()


def writeBarsToYFCSV(bars, filename, append):
    writer = BarsToCSV(filename, append, frequency=Frequency.DAY,
                       columns=['Date', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'],
                       delimiter=',')
    writer.writeBars(bars)
    writer.close()

@memoize(size=10)           # This is not for caching but to avoid repeated downloads for the current year
@retry(tries=5, delay=3)    # Retry 5 times with 3 seconds of intervals
def downloadCSV(filename, instrument, year, frequency):
    today = datetime.datetime.now().date()
    thisYear = today.year

    if frequency == Frequency.DAY:
        get_bars = googlefinance.get_google_1m_bars_for_year  # Hack to workaround YF API Change @ 20170517
        store_csv = writeBarsToYFCSV
        freqStr = "1D"
    elif frequency == Frequency.MINUTE:
        get_bars = iqfeed.get_1m_bars_for_year
        store_csv = writeBarsToNTCSV
        freqStr = "1M"
    else:
        log.error("Invalid CSV Frequency: %s", frequency)
        raise Exception("Invalid CSV Frequency: %s" % frequency)

    if not os.path.exists(filename) or year == thisYear:
        # Download from Yahoo finance
        log.info("Downloading %s backtest data for %s %d", freqStr, instrument, year)
        bars = get_bars(instrument, year)
        store_csv(bars, filename, append=False)

# Cache sizes for daily data (pypy-2.1):
#  100 items: ~ 180mb
# 1000 items: ~ 245mb
# 5000 items: ~ 550mb
# 6000 itmes: ~ 900mb
# 7000 items: ~ 1000mb
# Cache size for minute data (pypy-2.5alpha):
# 15 items: ~ 1000mb
#@memoize(size=1, lru=True)
def loadCSV(path, frequency):
    result = []

    # NinjaTrader row parser is used with minute bars (quantquote)
    # Yahoo row parser is used with the daily bars
    if frequency == Frequency.MINUTE:
        rowParser = IQRowParser(frequency, None, EasternTZ)
    else:
        rowParser = YHRowParser(datetime.time(9, 30, 0, 0, tzinfo=EasternTZ))

    # Read it
    if path.endswith('.gz'):
        fd = os.popen("gzip -c -d %s" % path, "r")
    else:
        fd = open(path, "r")

    reader = csv.DictReader(fd, fieldnames=rowParser.getFieldNames(), delimiter=rowParser.getDelimiter())
    for row in reader:
        bar_ = rowParser.parseBar(row)
        if bar_ is None:
            fd.close()
            log.error("Unable to parse CSV Data from file: %s", path)
            raise Exception("Unable to parse CSV Data from file: %s" % path)

        result.append(bar_)

    fd.close()

    # The bars are not in order this point, yahoo returns the data out of order
    result.sort(key=lambda bar: bar.getDateTime())

    return result

def loadHistoricalBars(instrument, startDate, endDate, frequency=Frequency.MINUTE, cacheDir=CSV_CACHE_DIR, offline=False):
    """Loads historical bars from local cache or from Interactive Brokers. 
    
    The local cache stores the historical data in csv files,
    one file per year. Filename format: HC-INSTR-YEAR.csv, where 
    HC Stands for HUBA Cache, INSTR is the instrument name (in upper case)
    and YEAR is the four digit year (like 2013).

    The format for the CSV file is matching with the Ninjatrader's CSV Format.

    :param instrument: Instrument name to download data for
    :type instrument:  string
    :param startDate: Beginning date of the time window.
    :type startDate:  :class:`datetime.date`
    :param endDate: End date of the time window.
    :type endDate:  :class:`datetime.date`
    """
    result = []

    # Include the Frequency string representation in the CSV filenames
    if frequency == Frequency.MINUTE:
        frequencyStr = "1M"
    else:
        frequencyStr = "1D"

    # Iterate through the years in between startDate and endDate
    for year in range(startDate.year, endDate.year + 1):
        # Download the CSV file if not exists
        if frequency == Frequency.DAY:
            filename = "%s/HC-%s-%s-%d.csv" % (cacheDir, instrument, frequencyStr, year)

            if not offline and frequencyStr == '1D':
                downloadCSV(filename, instrument, year, frequency)
            bars = loadCSV(filename, frequency)
            log.debug("Included %d bars from file: %s", len(bars), filename)
        elif frequency == Frequency.MINUTE:
            # Minutely data is downloaded using iqfeed
            csv_content = OrderedDict()
            for prefix in ["iqfeed.csv.gz", "ib-real.csv", "ib-paper.csv"]:
                filename = "%s/HC-%s-%s-%d-%s" % (cacheDir, instrument, frequencyStr, year, prefix)

                if os.path.exists(filename):
                    csv_content[filename] = loadCSV(filename, frequency)

            bars = []
            for filename in csv_content:
                if len(bars) == 0:
                    bars = csv_content[filename]
                    log.debug("Included %d bars from file: %s", len(bars), filename)
                else:
                    loadedBarStartDate = min([e.getDate() for e in bars])
                    loadedBarEndDate = max([e.getDate() for e in bars])
                    barsIncluded = 0
                    for bar in csv_content[filename]:
                        if bar.getDate() < loadedBarStartDate or  bar.getDate() > loadedBarEndDate:
                            bars.append(bar)
                            barsIncluded += 1
                    log.debug("Included %d (for period %s-%s) bars from file: %s (%d)",
                              barsIncluded, loadedBarStartDate, loadedBarEndDate, filename, len(csv_content[filename]))

        # Select the bars inside the specified time frame
        log.debug("Loaded sum of %d bars from file(s)", len(bars))
        for bar in bars:
            dt = bar.getDate()
            if startDate <= dt <= endDate:
                result.append(bar)
            elif endDate < dt:
                break

        log.debug("Left %d bars after filtering for time-frame", len(result))

    return result


def alignBarlist(barlist1, barlist2):
    """Select those bars whose timestamp is present in both list and return the modified barlists"""
    res1, res2 = [], []

    ds1DateTimes = [e.getDateTime() for e in barlist1]
    ds2DateTimes = [e.getDateTime() for e in barlist2]

    dateTimes, pos1, pos2 = intersect(ds1DateTimes, ds2DateTimes)
    for i in pos1:
        res1.append(barlist1[i])

    for i in pos2:
        res2.append(barlist2[i])

    return res1, res2


def logResultsToCSV(filename, results):
    fileExists = os.path.exists(filename)

    with open(filename, 'a') as csvFile:
        if fileExists:  # Seek to the end
            csvFile.seek(0, 2)

        csvWriter = csv.DictWriter(csvFile, results.keys())

        if not fileExists:  # Include the header
            csvWriter.writeheader()

        csvWriter.writerow(results)


def logTradeToCSV(tag, dateTime, pair, entryPrice0, exitPrice0, qty0, entryPrice1, exitPrice1, qty1, sumProfit, roi):
    filename = '%s/trades%s.csv' % (LOG_DIR, tag)
    od = OrderedDict()
    od['DateTime']    = dateTime
    od['Pair']        = pair
    od['EntryPrice0'] = "%.2f" % entryPrice0
    od['ExitPrice0']  = "%.2f" % exitPrice0
    od['Qty0']        = qty0
    od['EntryPrice1'] = "%.2f" % entryPrice1
    od['ExitPrice1']  = "%.2f" % exitPrice1
    od['Qty1']        = qty1
    od['SumProfit']   = "%.2f" % sumProfit
    od['ROI']         = "%.2f" % roi

    logResultsToCSV(filename, od)


def logEquityToCSV(tag, dateTime, equity):
    filename = '%s/equities%s.csv' % (LOG_DIR, tag)
    od = OrderedDict()
    od['DateTime'] = dateTime
    od['Equity']   = equity

    logResultsToCSV(filename, od)


def logDailyROIToCSV(tag, dateTime, pair, closedPosROI, closedPosCnt, tradeCnt,
                     inPosCapital, inPosROI0, inPosROI1, ROI):
    filename = '%s/dailyROI%s.csv' % (LOG_DIR, tag)
    od = OrderedDict()
    od['DateTime']      = dateTime
    od['Pair']          = pair
    od['ClosedPosROI']  = "%.2f" % closedPosROI
    od['ClosedPosCnt']  = "%d"   % closedPosCnt
    od['TradeCnt']      = "%d"   % tradeCnt
    od['InPosCapital']  = "%.2f" % inPosCapital
    od['InPosROI0']     = "%.2f" % inPosROI0
    od['InPosROI1']     = "%.2f" % inPosROI1
    od['ROI']           = "%.2f" % ROI

    logResultsToCSV(filename, od)


def expandDailyBars(bars):
    newBars = []

    for bar in bars:
        dt = bar.getDateTime()
        date_ = bar.getDate()
        openPrice = bar.getAdjOpen()
        highPrice = bar.getAdjHigh()
        lowPrice = bar.getAdjLow()
        closePrice = bar.getAdjClose()
        volume = bar.getVolume()

        open_ = Bar(datetime.datetime(dt.year, dt.month, dt.day, 9, 30, 00, 00, tzinfo=EasternTZ),
                    openPrice, openPrice, openPrice, openPrice, volume/4, openPrice, date_)
        high = Bar(datetime.datetime(dt.year, dt.month, dt.day, 11, 00, 00, 00, tzinfo=EasternTZ),
                    highPrice, highPrice, highPrice, highPrice, volume/4, highPrice, date_)
        low = Bar(datetime.datetime(dt.year, dt.month, dt.day, 14, 00, 00, 00, tzinfo=EasternTZ),
                    lowPrice, lowPrice, lowPrice, lowPrice, volume/4, lowPrice, date_)
        close = Bar(datetime.datetime(dt.year, dt.month, dt.day, 15, 55, 00, 00, tzinfo=EasternTZ),
                    closePrice, closePrice, closePrice, closePrice, volume/4, closePrice, date_)

        newBars.extend([open_, high, low, close])

    return newBars