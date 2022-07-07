__author__ = 'tiborkiss'

from datetime import datetime
import pytz

from pyalgotrade.tools import yahoofinance
from pyalgotrade.bar import Bar

# EasternTZ is also present in tools.csv_tools, but that would cause circular include
EasternTZ = pytz.timezone('US/Eastern')

def get_yahoo_1m_bars_for_year(instrument, year):
    headerRowSeen = False
    bars = []
    csvContent = yahoofinance.get_daily_csv(instrument, year)
    for line in csvContent.split('\n'):
        if len(line) == 0:
            # Skip empty lines
            continue

        if not headerRowSeen:
            if line != 'Date,Open,High,Low,Close,Volume,Adj Close':
                raise Exception("Invalid header row from yahoo: %s" % line)
            else:
                headerRowSeen = True
        (dtStr, open_, high, low, close, volume, adjClose) = line.split(',')

        if dtStr == 'Date':
            # Skip header row
            continue

        dt = datetime.strptime(dtStr, "%Y-%m-%d")
        dt = EasternTZ.localize(dt)
        bar = Bar(dt, float(open_), float(high), float(low), float(close), float(volume), float(adjClose))
        bars.append(bar)

    return bars


