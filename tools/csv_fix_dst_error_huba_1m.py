__author__ = 'tiborkiss'

import sys
import glob
import datetime
import csv

files = glob.glob("HC-*-1M-*_*.csv")

for file in files:
    print 'Processing %s' % file
    reader = csv.DictReader(open(file, "r"),
                            fieldnames=('DateTime', 'Open', 'High', 'Low', 'Close', 'Volume'),
                            delimiter=';')

    writer = csv.DictWriter(open(file + '-fixed', 'w'),
                            fieldnames=('DateTime', 'Open', 'High', 'Low', 'Close', 'Volume'),
                            delimiter=';')

    fix_dst = False
    rows = []

    # Read the whole file
    for row in reader:
        rows.append(row)

    # Skip empty files
    if len(rows) == 0:
        # Empty file
        continue

    if rows[-1]['DateTime'].find('1600') == -1:
        fix_dst = True

    for row in rows:
        dt = datetime.datetime.strptime(row['DateTime'], '%Y%m%d %H%M%S')

        if fix_dst:
            row['DateTime'] = (dt + datetime.timedelta(hours=1)).strftime('%Y%m%d %H%M%S')

        writer.writerow(row)

    #sys.exit(1)