#!/usr/bin/env python

import glob
import csv
import sys
import os

def load_processed_pairs(backtest_csv_glob):
    files = glob.glob(backtest_csv_glob)

    pairs = set()
    for file_ in files:
        with open(file_, "r") as f:
            csv_ = csv.DictReader(f)

            for row in csv_:
                pairs.add(row['Pairs'])

    return pairs

def process_original_list(filename, processed_pairs):
    new_filename = '%s.old' % filename
    os.rename(filename, new_filename)

    with open(new_filename, 'r') as f_read:
        with open(filename, 'w') as f_write:
            for line in f_read:
                if line.strip() not in processed_pairs:
                    f_write.write(line)
                else:
                    print 'Skip: %s' % line


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print 'Usage:'
        print '%s stocks.list "/path/to/logs/backtest-foo*.csv"'
        sys.exit(-1)

    processed_pairs = load_processed_pairs(sys.argv[2])
    process_original_list(sys.argv[1], processed_pairs)

