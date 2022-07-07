#!/usr/bin/env python2.7
# CSV Transform script for Google Intraday data
# This script processes the 1M weekly downloaded data by fetch_google_intraday.py
# and accumulates into csv files by year
#
# Duplicate bars are present in the source csv entries are removed


__author__ = 'tiborkiss'

import sys
import glob
import csv
from collections import OrderedDict
from datetime import datetime


# Accumulate all the weekly into yearly
# Exchange separator: , -> ;
# Check for duplicates

GOOGLE_INTRA_LOC='backtestdata/googleintra'
CSVCACHE_LOC='.csvCache'


def usage():
    print 'Usage:'
    print './csv_xform_google_intraday.py INSTR1 [INSTR2, ...]'


def main(argv):
    print argv
    if len(argv) < 1:
        usage()
        sys.exit()

    for instr in argv:
        files = glob.glob('%s/GF-%s*csv' % (GOOGLE_INTRA_LOC, instr))
        files.sort()

        # Trick is that we are using an ordered-dict and storing the OHLC values with dateTime as
        # the key. This way the newer values are overwriting the older ones, effectively solving
        # the duplicate entry issues.
        years = OrderedDict()  # Dict in a dict: keys are years, then keys are dateTimes in str
        for file in files:
            print 'Processing %s' % file
            reader = csv.DictReader(open(file, "r"),
                                    fieldnames=('DateTime', 'Open', 'High', 'Low', 'Close', 'Volume'),
                                    delimiter=',')

            for row in reader:
                year = datetime.strptime(row['DateTime'], '%Y%m%d %H%M%S').year
                years.setdefault(year, OrderedDict())
                years[year][row['DateTime']] = (row['Open'], row['High'], row['Low'], row['Close'], row['Volume'])

        for year in years:
            file = '%s/HC-%s-1M-%s-google.csv' % (CSVCACHE_LOC, instr, year)
            print 'Creating %s' % file

            writer = csv.writer(open(file, 'w'), delimiter=';')
            for dateTime in years[year]:
                row = years[year][dateTime]
                writer.writerow((dateTime, ) + row)

if __name__ == '__main__':
    main(sys.argv[1:])
