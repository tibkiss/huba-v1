__author__ = 'tiborkiss'

import datetime
import yql
import pandas as pd

import logging

from tools import PYALGOTRADE_PATH
import sys, os
sys.path.append(PYALGOTRADE_PATH)


from pyalgotrade.barfeed import Frequency
from pyalgotrade.utils.cache import memoize

from tools import retry
from tools.csv_tools import loadHistoricalBars

log = logging.getLogger(__name__)

# Max investment: $200k/20 pair = $5k per stock
MAX_CAPITAL_PER_STOCK = 5000

# Date ranges
BT_START_DATE = datetime.date(2007, 1, 1)
BT_END_DATE = datetime.date(2013, 12, 31)

@memoize
@retry(tries=5, delay=6)
def yql_query(symbol):
    # Create YQL connection
    y = yql.Public()

    query = 'select AverageDailyVolume, YearLow from yahoo.finance.quotes where symbol = "%s"' % symbol

    yres = y.execute(query, env="store://datatables.org/alltableswithkeys")

    # print yres.rows

    if len(yres.rows) != 1:
        raise Exception("YQL Download failed: %s" % str(yres.rows))

    try:
        avgDailyVolume = float(yres.rows[0]['AverageDailyVolume'])
        yearLow = float(yres.rows[0]['YearLow'])
    except TypeError:
        avgDailyVolume = pd.np.NaN
        yearLow = pd.np.NaN

    return avgDailyVolume, yearLow


def prefilter_stocks(stockList):
    res = []

    for i, symbol in enumerate(stockList):
        try:
            log.info('Processing %s, %d more to go, %d is valid' % (symbol, len(stockList) - i, len(res)))

            # Query yahoo
            avgDailyVolume, yearLow = yql_query(symbol)

            log.info("Stock: %s,%s,%s" % (symbol, avgDailyVolume, yearLow))

            # Filter for price, should be bigger than $5
            if yearLow < 5.0:
                continue

            # Filter for volume
            # Maximal stock count (max 1% of daily vol): ($10k/YearLow) * 100
            if avgDailyVolume < (MAX_CAPITAL_PER_STOCK / yearLow) * 100:
                continue

            # Try to load the backtest data
            bars = loadHistoricalBars(symbol, BT_START_DATE, BT_END_DATE, frequency=Frequency.DAY, offline=False)
            log.info('Historical bar count: %d' % len(bars))

            # Require at least 4 years worth of data
            if len(bars) < 1000:
                log.info("Invalid, bars are truncated: %s" % symbol)
                continue

            log.info('Valid: %s' % symbol)
            res.append(symbol)
        except Exception:
            log.info('Exception during evaluation: %s ' % symbol)

    return res



if __name__ == '__main__':
    if len(sys.argv) < 3:
        print 'Usage:'
        print '%s result file1 file2 ... fileN'
        sys.exit()

    if os.path.exists(sys.argv[1]):
        print 'Result file already exists'
        sys.exit()

    logging.basicConfig()
    log = logging.getLogger()
    log.setLevel(logging.INFO)

    stockList = []
    for i in sys.argv[2:]:
        with open(i, 'r') as f:
            for line in f:
                stockList.append(line.strip().upper())

    stockRes = prefilter_stocks(stockList)

    if len(stockRes) > 0:
        with open(sys.argv[1], 'w') as f:
            f.write("\n".join(stockRes))
