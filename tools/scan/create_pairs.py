__author__ = 'tiborkiss'

import sys
from itertools import combinations

def create_pairs(files):
    symbols = []
    for filename in files:
        with open(filename, 'r') as f:
            for line in f:
                symbols.append(line.strip())

    # Symbols:
    print len(symbols)

    pairs = combinations(symbols, 2)
    for pair in pairs:
        print "_".join(pair)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Usage: %s symbols1.lst symbols2.lst ... symbolsN.lst' % sys.argv[0]
        sys.exit()

    create_pairs(sys.argv[1:])
