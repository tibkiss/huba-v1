#!/usr/bin/env python

from config import StatArbPairsParams
from itertools import chain
import urllib2

def load_pilot_db():
    urls = ['http://www.nasdaqtrader.com/Files/ticksizepilot/TSPilotSecurities_20170320.txt',
            'ftp://ftp.nyxdata.com/Tick_Pilot/Tick_Pilot_Historical/NYSE_Group_Tick_Pilot_Assignments.txt']

    pilot_db = []

    for url in urls:
        print 'Downloading: %s' % url
        response = urllib2.urlopen(url)
        content = response.readlines()

        pilot_db.extend(content)

    return pilot_db

def find_in_pilot_db(instr, pilot_db):
    pattern = "%s|" % instr
    return any([line.startswith(pattern) for line in pilot_db])


def get_instr_with_no_increment():
    instrument_increment_tuple = chain.from_iterable([zip(pair, StatArbPairsParams[param_key][pair].limitPriceIncrements)
                                                      for param_key in StatArbPairsParams
                                                      for pair in StatArbPairsParams[param_key]])

    instrument_increment_tuple_with_no_increments = filter(lambda x: x[1] is None, instrument_increment_tuple)
    instruments_with_no_increments = set(x[0] for x in instrument_increment_tuple_with_no_increments)

    return instruments_with_no_increments

def main():
    instruments_to_check = get_instr_with_no_increment()
    pilot_db = load_pilot_db()

    # print instruments_to_check

    instruments_to_add_increment = filter(lambda instrument: find_in_pilot_db(instrument, pilot_db), instruments_to_check)

    print 'Instruments needs price increments added:'
    print sorted(instruments_to_add_increment)


if __name__ == '__main__':
    main()