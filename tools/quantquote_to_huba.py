__author__ = 'tiborkiss'

import csv
import sys
import datetime
import os
import argparse

# QuantQuote fields of the default format:
# Date, Time, Open, High, Low, Close, Volume, Splits, Earnings, Dividends
fieldnames=['Date', 'Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Splits', 'Earnings', 'Dividends']
dayStart = datetime.time(9,30)
dayEnd = datetime.time(16,00)

def qqcsv_to_hc(srcFilename, dstDirname, symbol):
    """Convert QuantQuote.com CSV file format to NinjaTrade format split up by years"""
    reader = csv.DictReader(open(srcFilename, "r"), fieldnames, delimiter=',')

    # Some safety
    if srcFilename.upper().find(symbol) == -1:
        print 'Symbol is not found in filename: %s - %s' % (symbol, srcFilename)
        return

    lastYear = None
    outFile = None
    for row in reader:
        dtstr = "%s %s" % (row['Date'], row['Time'])
        dt = datetime.datetime.strptime(dtstr, '%Y%m%d %H%M')

        if dt.year != lastYear:
            if outFile is not None:
                outFile.close()

            outFilename = "%s/HC-%s-1M-%s.csv" % (dstDirname, symbol, dt.year)
            print 'Processing %s' % outFilename
            if os.path.exists(outFilename):
                print '%s already exists!' % outFilename
                return

            outFile = open(outFilename, "w")
            #outFile.write("Date Time;Open;High;Low;Close;Volume\n")  # Header

            lastYear = dt.year

        if dayStart <= dt.time() <= dayEnd:
            # Only RTH
            dtstr = dt.strftime("%Y%m%d %H%M%S")
            outRow = '%s;%s;%s;%s;%s;%s\n' % (dtstr, row['Open'], row['High'], row['Low'], row['Close'], row['Volume'])
            outFile.write(outRow)

    if outFile is not None:
        outFile.close()


def main():
    parser = argparse.ArgumentParser(description='HUBA - QuantQuote to HubaCache converter')
    parser.add_argument('--src-file',        help='Source file', default=None)
    parser.add_argument('--dst-dir',         help='Destination directory', default=None)
    parser.add_argument('--symbol',         help='Symbol name', default=None)
    args = parser.parse_args()

    if args.src_file is None:
        print 'src-file is missing'
        return

    if args.dst_dir is None:
        print 'dst-dir is missing'
        return

    if args.symbol is None:
        print 'symbol is missing'
        return

    qqcsv_to_hc(args.src_file, args.dst_dir, args.symbol.upper())

if __name__ == '__main__':
    main()