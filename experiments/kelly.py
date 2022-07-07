#!/usr/bin/env python
# Kelly formula calculation based on 
# Ernest P... Chan's Quantitative Trading book (pg. 100)
# 
# Dependencies: Numpy, Pandas
# 
# 2014 - Tibor Kiss - <tibor.kiss@gmail.com>

import sys
import datetime

import pandas.io.data as web
from pandas import DataFrame

from numpy.linalg import inv

RISK_FREE_RATE = 0.04  # Annualized

def calc_kelly_leverages(symbols, start, end):
    f = {}
    ret = {}
    excRet = {}
    for symbol in symbols:
        # print "Downloading historical prices for: ", symbol
        hist_prices = web.DataReader(symbol, 'yahoo', start, end)
        f[symbol] = hist_prices

        # ret[symbol] = (hist_prices['Adj Close'] - hist_prices['Adj Close'].shift(1)) / hist_prices['Adj Close'].shift(1)
        ret[symbol] = hist_prices['Adj Close'].pct_change()
        excRet[symbol] = (ret[symbol] - (RISK_FREE_RATE/252))

    df = DataFrame(excRet).dropna()
    C = 252 * df.cov() 
    M = 252 * df.mean()
    F = inv(C).dot(M)

    print "Leverages: "
    for (name, val) in zip(df.columns.values.tolist(), F):
        print "%s: %.2f" % (name, val)
    print "Sum leverage: %.2f " % sum(F)
    print ""

def main(args):
    # Ernie's example
    # print "Kelly for Ernie's example:"
    # start = datetime.datetime(2001, 2, 26)
    # end = datetime.datetime(2007, 12, 28)
    # calc_kelly_leverages(['OIH', 'RKH', 'RTH'], start, end)

    print "Kelly for custom portfolio:"
    start = datetime.datetime(2010, 1, 1)
    end = datetime.datetime(2014, 12, 1)
    # calc_kelly_leverages(['EDEN', 'EFAV', 'EWD', 'IBB', 'IHI', 'MA', 'MU', 'SPLV', 'SPY', 'TSLA', 'V', 'VCR', 'VHT'], start, end)
    calc_kelly_leverages(args, start, end)


if __name__ == '__main__':
    main(sys.argv[1:])


