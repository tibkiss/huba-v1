import csv
import sys
import config


def load_csv(filename):
    rows = []
    reader = csv.DictReader(open(filename, 'r'))
    for row in reader:
        rows.append(row)

    return rows

def main(args):
    trades_csv = load_csv(args[1])

    for pair in config.StatArbConfig['Paper']['Pairs']:
        trades = [e for e in trades_csv if e['Pair'] == pair]
        print '%s -> %d' % (pair, len(trades))


    #print trades_csv


if __name__ == '__main__':
    main(sys.argv)