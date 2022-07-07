#!/usr/bin/env python2.7

import sys
import pandas as pd

import config as huba_cfg

def main(args):
    c = pd.read_csv(args[0])
    all_pairs = huba_cfg.StatArbPairsConfig.keys()

    pairs_pnl = {}
    for pair in all_pairs:
        pairs_pnl[pair] = c[(c['Symbol'] == pair[0]) | (c['Symbol'] == pair[1])].TotalRealizedPnl.sum()

    # Convert dict to dataframe
    pairs_pnl = pd.DataFrame(list(pairs_pnl.iteritems()), columns=('Symbol', 'TotalRealizedPnl'))

    print pairs_pnl.sort('TotalRealizedPnl')


if __name__ == '__main__':
    main(sys.argv[1:])
