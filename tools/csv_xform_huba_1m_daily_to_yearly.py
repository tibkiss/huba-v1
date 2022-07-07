#!/usr/bin/env python2.7

import sys, os, glob


# Get stocks in shell with:
# .csvCache $ stocks=`ls  | grep -- "-1M-" | grep "_" | cut -f 2 -d "-" | sort | uniq`
stocks = os.environ.get('stocks').split()  

for typ_ in ('paper', 'real'):
    for stock in stocks:
        for year in (2014, 2013):
            csvFiles = glob.glob("HC-%s-1M-%s*-%s.csv" % (stock, year, typ_))
            csvFiles.sort()

            if len(csvFiles) == 0:
                continue

            dstFilename = "final/HC-%s-1M-%s-%s.csv" % (stock, year, typ_)
            print 'creating %s' % dstFilename

            with open(dstFilename, "a") as dstFile:
                dstFile.seek(0, 2)

                for filename in csvFiles:
                    if filename == dstFilename:
                        continue

                    #print 'open: %s' % filename

                    with open(filename, "r") as inFile:
                        dstFile.writelines(inFile.readlines())

