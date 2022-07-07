
import argparse
import csv

from tools.csv_tools import writeBarsToNTCSV
from tools import downscaleBarsInTime

from pyalgotrade.barfeed import Frequency
from pyalgotrade.barfeed.iqfeed import RowParser

import pytz

def downscaleCSV(infile, outfile):
    # Create rowparser
    rowParser = RowParser(Frequency.MINUTE, None, pytz.timezone("US/Eastern"))

    # Create list for the loaded bars
    loadedBars = []

    # Read it
    reader = csv.DictReader(open(infile, "r"), fieldnames=rowParser.getFieldNames(), delimiter=rowParser.getDelimiter())
    for row in reader:
        bar_ = rowParser.parseBar(row)
        if bar_ is None:
            print "Unable to parse CSV Data from file: %s" % infile
            raise SystemError()

        loadedBars.append(bar_)

    loadedBars = downscaleBarsInTime(loadedBars, minutes=1440)
    writeBarsToNTCSV(loadedBars, outfile, append=False)


def main():
    parser = argparse.ArgumentParser(description='HUBA - Highly Unorthodox Broker Agent - Downscale Bars')
    parser.add_argument('--in-file', help='Input file', nargs=1, default=None)
    parser.add_argument('--out-file', help='Output file', nargs=1, default=None)
    args = parser.parse_args()

    if args.in_file is None or args.out_file is None:
        print 'Infile or outfile missing'
        return

    downscaleCSV(args.in_file[0], args.out_file[0])


if __name__ == '__main__':
    main()