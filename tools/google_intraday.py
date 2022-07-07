#!/usr/bin/env python2.7
"""google_intraday: Intraday 1M data downloader for Google
      Tibor Kiss <tibor.kiss@gmail.com> - Copyright (c) 2012-2014 All rights reserved

Usage:
  google_intraday.py get-traded <days> [-v]
  google_intraday.py get-from-file <filename> <days>
  google_intraday.py <stock> <days> [-v]
  google_intraday.py -h | --help

Commands:
  get-quantile      Load all the available pairs (from huba config, s&p, russell) and divide them into 5 days
                    Useful to split up the work to one week for cron jobs.
Options:
  -v               Verbose mode
  -h               Help screen

"""

import urllib, datetime

from math import ceil

import sys
import logging
log = logging.getLogger(__name__)

from tools import CSV_CACHE_DIR
from tools import get_monitored_stock_list, get_instruments_from_txt, get_huba_instruments
from tools import get_git_version
from tools.csv_tools import writeBarsToNTCSV, EasternTZ
from tools.docopt import docopt
from tools import retry

from pyalgotrade.bar import Bar
from pyalgotrade.barfeed import Frequency


class Quote(object):
    def __init__(self):
        self.symbol = ''
        self.dt, self.open_, self.high, self.low, self.close, self.volume = ([] for _ in range(6))

    def append(self, dt, open_, high, low, close, volume):
        self.dt.append(dt)
        self.open_.append(float(open_))
        self.high.append(float(high))
        self.low.append(float(low))
        self.close.append(float(close))
        self.volume.append(int(volume))

    def write_csv(self, filename):
        bars = []
        for i in xrange(len(self.close)):
            bar = Bar(self.dt[i], self.open_[i], self.high[i], self.low[i], self.close[i], self.volume[i],
                      adjClose=self.close[i])
            bars.append(bar)

        writeBarsToNTCSV(bars, filename, append=True)

    def __repr__(self):
        return ''.join(["{0};{1:.4f};{2:.4f};{3:.4f};{4:.4f};{5}\n".format(
                        self.dt[bar].strftime('%Y%m%d %H%M%S'),
                        self.open_[bar], self.high[bar], self.low[bar], self.close[bar], self.volume[bar])
                       for bar in xrange(len(self.close))])


class GoogleIntradayQuote(Quote):
    ''' Intraday quotes from Google. Specify interval seconds and number of days '''
    def __init__(self, symbol, interval_seconds=300, num_days=5):
        super(GoogleIntradayQuote, self).__init__()
        self.symbol = symbol.upper()
        self.interval = interval_seconds
        self.num_days = num_days

    @retry(tries=5, delay=3)
    def getQuote(self):
        url_string = "http://www.google.com/finance/getprices?q={0}".format(self.symbol)
        url_string += "&i={0}&p={1}d&f=d,o,h,l,c,v".format(self.interval, self.num_days)
        csv = urllib.urlopen(url_string).readlines()
        for bar in xrange(7, len(csv)):
            if csv[bar].count(',') != 5:
                continue

            offset, close, high, low, open_, volume = csv[bar].split(',')

            if offset[0] == 'a':
                day = float(offset[1:])
                offset = 0
            else:
                offset = float(offset)

            open_, high, low, close = [float(x) for x in [open_, high, low, close]]
            dt = datetime.datetime.fromtimestamp(day+(self.interval * offset), tz=EasternTZ)
            self.append(dt, open_, high, low, close, volume)

def download_google_intra(stock, days):
    year = datetime.datetime.now().year
    interval_seconds = 60

    filename = '%s/HC-%s-1M-%s-google.csv' % (CSV_CACHE_DIR, stock, year)
    log.info("Downloading to %s", filename)

    q = GoogleIntradayQuote(stock, interval_seconds, days)
    q.getQuote()

    q.write_csv(filename)

def main(args):
    args = docopt(__doc__, argv=args, version=get_git_version())

    if args['get-traded']:
        stocks = get_huba_instruments()
    elif args['get-from-file']:
        stocks = get_instruments_from_txt(args['<filename>'])
    elif args['<stock>']:
        stocks = [args['<stock>'], ]

    for stock in stocks:
        try:
            download_google_intra(stock, int(args['<days>']))
        except Exception as e:
            log.error('Exception: %s', str(e))

if __name__ == '__main__':
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    logConsole = logging.StreamHandler(sys.stdout)
    logConsole.setLevel(logging.INFO)
    log.addHandler(logConsole)
    main(sys.argv[1:])
