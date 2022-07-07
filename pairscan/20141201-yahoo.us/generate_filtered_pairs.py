#!/usr/bin/env python2.7

import glob

industry_pairs = glob.glob('*.pairs')

acceptable_stocks = []
with open('yahoo.us.symbols.filtered', 'r') as f:
    for line in f:
        line = line.rstrip()
        acceptable_stocks.append(line)

print 'Read %d acceptable stocks' % len(acceptable_stocks)

for i in industry_pairs:
    print 'Processing %s' % i
    with open(i, 'r') as input:
        with open('%s.filtered' % i, 'w') as output:
            for line in input:
                line = line.rstrip()
                instr0, instr1 = line.split('_')

                if instr0 in acceptable_stocks and instr1 in acceptable_stocks:
                    output.write('%s\n' % line)
                    # print '%s is good' % line
