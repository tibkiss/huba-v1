import logging
log = logging.getLogger(__name__)

import os, sys, traceback, math
from dateutil import rrule
from datetime import datetime, timedelta
import pytz
import time
from functools import wraps
import subprocess
import collections


DT_FMT = "%y-%m-%d %H:%M:%S"  # Datetime format string
IS_PYPY = '__pypy__' in sys.builtin_module_names

# We are located under tools, parent dir is the root
HUBA_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__) + '/../'))
LOG_DIR = "%s/logs" % HUBA_DIR
CSV_CACHE_DIR = "%s/.csvCache" % HUBA_DIR
PYALGOTRADE_PATH = "%s/../pyalgotrade" % HUBA_DIR  # Add pyalgotrade to (python)path
sys.path.append(PYALGOTRADE_PATH)

SP_500 = '%s/backtestdata/sp-500.txt' % HUBA_DIR
RUSSELL_3000 = '%s/backtestdata/russell-3000.txt' % HUBA_DIR
ETFDB_FILTERED = '%s/backtestdata/etfdb.all.noinv.nolev.symbols.filtered' % HUBA_DIR

from pyalgotrade.broker import Order
from pyalgotrade.broker import backtesting
from pyalgotrade.bar import Bar
from pyalgotrade.utils.cache import memoize


def priceRound(x, precision=2, base=0.05):
    return round(base * round(float(x)/base), precision)

def rint(num):
    """Rounds toward the even number if equidistant"""
    return round(num + (num % 2 - 1 if (num % 1 == 0.5) else 0))


def reduceBars(bars, dateTime=None):
    """Summarize a set of bars into one pyalgotrade.bar.Bar instance:
    Bar.DateTime will be the given dateTime or the datetime of the first  element from the bar list
    Bar.Open will be the open price of the first element from the bar list
    Bar.Close will be the close price of the last element from the bar list
    Bar.High will be the highest price from the bar list
    Bar.Low will be the lowest price from the bar list
    Bar.Volume will be the summarized volume of the bar list
    """
    if dateTime is None:
        dateTime = bars[0].getDateTime()
    open_ = bars[0].getOpen()
    close = bars[-1].getClose()
    high = -1
    low = float("Inf")
    volume = 0
    for bar in bars:
        bar_high = bar.getHigh()
        bar_low = bar.getLow()
        if bar_high > high:
            high = bar_high
        if bar_low < low:
            low = bar_low
        volume += bar.getVolume()
    adjClose = bars[-1].getAdjClose()
    bar = Bar(dateTime, open_, high, low, close, volume, adjClose)

    return bar


def downscaleBars(bars, ticks):
    result = []
    for i in range(0, len(bars), ticks):
        if i+ticks > len(bars): 
            # skip incomplete ticks
            break
        bar = reduceBars(bars[i:i+ticks])
        result.append(bar)

    return result


def downscaleBarsInTime(bars, minutes):
    """Downscale bars to the defined timeslice.
    The minutes parameter defines the downscaled bars frequency,
    if set to 5, five minute bars are created, if set to 1440 daily bars are created

    Warning: the returned bars' timezone will be UTC!"""
    result = []
    # Need to start with the startDate at 00:00 in order to have the timestamps aligned correctly
    # If we would start with the first timestamp the sequence might not start in the proper minute.
    # The end should be the last bars _datetime_ plus the minutes to include all the bars from the last day.
    startDate = bars[0].getDateTime()
    startDate = datetime(startDate.year, startDate.month, startDate.day, 0, 0, 0, 0, pytz.utc)
    endDateTime = bars[-1].getDateTime() + timedelta(minutes=minutes)

    prevTs = None
    barPos = 0  # Used to position in the bars list

    # Create a minute sequence between the first bar's day and last bar's timestamp
    for ts in rrule.rrule(freq=rrule.MINUTELY, interval=minutes, dtstart=startDate, until=endDateTime):
        # We need two timestamps to define a time-range. Initialize the previous ts in the first run
        if prevTs is None:
            prevTs = ts
            continue

        frame = []
        # Select the bars for the prevTs - ts timeframe
        for bar in bars[barPos:]:
            if prevTs <= bar.getDateTime() < ts:
                # Include if it is in between the two timestamps
                frame.append(bar)
            elif ts < bar.getDateTime():
                # Stop iterating if we passed by the upper timestamp
                break

        if len(frame) > 0:
            # If we have data in the current frame reduce it to have one bar
            # with the proper timestamp
            reducedBar = reduceBars(frame, prevTs)
            result.append(reducedBar)

            barPos += len(frame)  # Adjust the position in the bars list

        prevTs = ts

    return result


def retry(tries, exceptions=None, delay=0):
    """
    Decorator for retrying a function if exception occurs

    tries -- num tries
    exceptions -- exceptions to catch
    delay -- wait between retries
    """
    exceptions_ = exceptions or (Exception, )
    def _retry(fn):
        @wraps(fn)
        def __retry(*args, **kwargs):
            for _ in xrange(tries+1):
                try:
                    return fn(*args, **kwargs)
                except exceptions_, e:
                    log.warning("Exception, retrying...", exc_info=e)
                    time.sleep(delay)
            #if no success after tries raise last exception
            raise
        return __retry
    return _retry


def log_exception(detailed=True):
    """ Print the usual traceback informatio, followed by a listing of
        all the local variables in each frame.

        From Python Cookbook 2nd edition (Martelli et. al)
    """
    tb = sys.exc_info()[2]
    while tb.tb_next:
        tb = tb.tb_next
    stack = []
    f = tb.tb_frame
    while f:
        stack.append(f)
        f = f.f_back
    stack.reverse()

    log.error("---------------------------< EXCEPTION >---------------------------")
    if detailed:
        for frame in stack:
            log.error("")
            log.error("Frame %s in %s at line %s" % (frame.f_code.co_name, frame.f_code.co_filename, frame.f_lineno))

            for key, value in frame.f_locals.items():
                msg = "\t%20s = " % key
                # we must _absolutely_ avoid propagating exceptions, and str(value)
                # COULD cause any exception se we MUST cache any...:
                try:
                    valueStr = str(value).split('\n')
                    valueStr = valueStr[0][0:120]   # First line's first 120 chars
                    msg = '%s %s' % (msg, valueStr)
                except:
                    msg = "%s <ERROR WHILE PRINTING VALUE>" % msg
                log.error(msg)

    # Basic info
    log.error("")
    exc_type, exc_value, exc_traceback = sys.exc_info()
    for item in traceback.format_exception(exc_type, exc_value, exc_traceback):
        for line in item.split('\n'):
            log.error(line)


    log.error("-------------------------------------------------------------------")

class RealistFillStrategy(backtesting.DefaultStrategy):
    def fillMarketOrder(self, order, broker_, bar):
        price = (bar.getAdjOpen() + bar.getAdjHigh() + bar.getAdjLow() + bar.getAdjClose()) / 4.0
        return price


class PessimistFillStrategy(backtesting.DefaultStrategy):
    def fillStopLimitOrder(self, order, broker_, bar, justHitStopPrice):
        return None

    def fillMarketOrder(self, order, broker_, bar):
        # TODO: Add slippage
        if order.getAction() in (Order.Action.BUY, Order.Action.BUY_TO_COVER):
            return bar.getHigh()
        elif order.getAction() in (Order.Action.SELL, Order.Action.SELL_SHORT):
            return bar.getLow()
        else:
            return None

    def fillStopOrder(self, order, broker_, bar):
        # TODO: Add slippage
        return None


class ATR(object):
    def __init__(self, period):
        self._period = period
        self._trs    = []
        self._atrs   = []

    def onBar(self, bar):
        if len(self._atrs) == 0:
            # we have not reached period yet,
            # the initial ATR is not created
            if len(self._trs) == 0:
                # Previous bar unknown, first value is always
                # High - Low
                self._trs.append(bar.getHigh() - bar.getLow())
                self._prevBar = bar
                return
            elif 0 < len(self._trs) < (self._period - 1):
                # Starting from second bar calculate the TR
                val1 = bar.getHigh() - bar.getLow()
                val2 = math.fabs(bar.getHigh() - self._prevBar.getClose())
                val3 = math.fabs(bar.getLow() - self._prevBar.getClose())
                self._trs.append(max(val1,val2,val3))
                self._prevBar = bar
            elif len(self._trs) == (self._period - 1):
                # Last TR needed to calculate first ATR
                val1 = bar.getHigh() - bar.getLow()
                val2 = math.fabs(bar.getHigh() - self._prevBar.getClose())
                val3 = math.fabs(bar.getLow() - self._prevBar.getClose())
                self._trs.append(max(val1,val2,val3))
                self._prevBar = bar

                # The first ATR is the average of the trs
                atr = sum(self._trs) / self._period
                self._atrs.append(atr)
        else:
            val1 = bar.getHigh() - bar.getLow()
            val2 = math.fabs(bar.getHigh() - self._prevBar.getClose())
            val3 = math.fabs(bar.getLow() - self._prevBar.getClose())
            self._trs.append(max(val1,val2,val3))
            self._prevBar = bar

            atr = (self._atrs[-1] * (self._period -1) + self._trs[-1]) / self._period
            self._atrs.append(atr)
        
    def getATR(self, pos=None):
        if not pos:
            pos = -1

        return self._atrs[pos]


def softAssert(expr):
    if not expr:
        log.error("Assertion error:")
        
        code = []
        for threadId, stack in sys._current_frames().items():
            code.append("\n# ThreadID: %s" % threadId)
            for filename, lineno, name, line in traceback.extract_stack(stack):
                code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
                if line:
                    code.append("  %s" % (line.strip()))
            
        for line in code:
            log.error("%s" % (line))


def attributesFromDict(d):
    """From Python Cookbook, Section 6.18"""
    self = d.pop('self')
    for n, v in d.iteritems():
        setattr(self, n, v)

class LogFilter(logging.Filter):
    """Simple text based log filter for logging"""
    def __init__(self, text):
        self._text = text

    def filter(self, record):
        return not record.getMessage().find(self._text) != -1

# From: http://code.activestate.com/recipes/576694/
class OrderedSet(collections.MutableSet):

    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, next = self.map.pop(key)
            prev[2] = next
            next[1] = prev

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)

@memoize(size=1)
def get_git_version():
    version = 'vX-unknown'
    prevDir = os.getcwd()
    os.chdir(os.path.dirname(__file__))

    try:
        p = subprocess.Popen(["git", "describe",
                              "--tags", "--always"],
                             stdout=subprocess.PIPE)
        stdout = p.communicate()[0]
        if p.returncode == 0 and stdout.startswith('v'):
            version = stdout.rstrip('\n')
    except EnvironmentError:
        pass

    os.chdir(prevDir)

    return version

def get_huba_instruments():
    # The StatArbPairsConfig must be imported here and not in module level
    # Since statarb.py imports this file we would make a circular import in case of module level declaration
    from config import StatArbPairsConfig
    instruments = set()
    for typ in ('Paper', 'Real'):
        for pairs in StatArbPairsConfig[typ]:
            for instrument in pairs:
                instruments.add(instrument)
    return instruments


def get_instruments_from_txt(filename):
    # Load index from txt file
    instruments = []
    with open(filename, 'r') as f:
        for instrument in f:
            instruments.append(instrument.rstrip())
    return instruments


def get_monitored_stock_list():
    # We would like to load etfdb, russell 3000 and s&p 500 instruments
    instrument_sets = {'etfdb':   OrderedSet(get_instruments_from_txt(ETFDB_FILTERED)),
                       's&p':     OrderedSet(get_instruments_from_txt(SP_500)),
                       'russell': OrderedSet(get_instruments_from_txt(RUSSELL_3000))}

    instruments = list(instrument_sets['etfdb'].union(instrument_sets['s&p']).union(instrument_sets['russell']))

    return instruments
