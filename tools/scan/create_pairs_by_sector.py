#!/usr/bin/env python

from csv import DictReader
import sys
from itertools import combinations


def create_pairs_by_group(symbols, base_filename, group):
    pair_of_tuples = combinations(symbols, 2)

    pair_list_filename = '%s-%s.lst' % (base_filename.replace('.lst', ''), group.replace('/','_').replace(' ', '_'))
    print 'Creating: %s, number of stocks: %d' % (pair_list_filename, len(symbols))

    with open('%s' % pair_list_filename, 'w') as f:
        for pair in pair_of_tuples:
            f.write("%s_%s\n" % (pair[0], pair[1]))

def create_pairs(filename, stock_to_sector):
    symbols = set()
    sectors = set(stock_to_sector.values())

    with open(filename, 'r') as f:
        for line in f:
            symbols.add(line.strip())

    processed_symbols = set()

    for sector in sectors:
        stocks_per_sector = [e for e in symbols if e in stock_to_sector and stock_to_sector[e] == sector]

        for stock in stocks_per_sector:
            processed_symbols.add(stock)

        create_pairs_by_group(stocks_per_sector, filename, sector)

    remaining_stocks = symbols - processed_symbols
    create_pairs_by_group(remaining_stocks, filename, 'unknownsector')


def get_stock_to_sector(filenames):
    stock_to_sector = {}

    for filename in filenames:
        with open(filename, "r") as f:
            csv_reader = DictReader(f)

            for row in csv_reader:
                stock_to_sector[row['Symbol']] = row['Sector']

    return stock_to_sector

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Usage: %s symbol.lst companylist-nyse.csv companylist-nasdaq.csv' % sys.argv[0]
        sys.exit()

    stock_to_sector = get_stock_to_sector([sys.argv[2], sys.argv[3]])

    create_pairs(sys.argv[1], stock_to_sector)
