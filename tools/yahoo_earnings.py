#!/usr/bin/env python
"""yahoo_earnings: Yahoo Earnings data downloader
      Tibor Kiss <tibor.kiss@gmail.com> - Copyright (c) 2012-2015 All rights reserved

Usage:
  yahoo_events.py get-traded [-svd]
  yahoo_events.py get-from-file <filename> [-svd]
  yahoo_events.py <stock> [-svd]
  yahoo_events.py -h | --help

Options:
  -s --store-in-db    Store events in db
  -v --verbose        Verbose mode
  -d --debug          Debug mode
  -h                  Help screen

"""

import sys
import logging
from httplib2 import Http

from datetime import datetime

from docopt import docopt
import yql

from tools.db import DBHandler
from tools import get_huba_instruments, get_instruments_from_txt, get_git_version
from tools import retry
from config import HUBA_DB_URI

log = logging.getLogger(__name__)


@retry(tries=5)
def get_current_events(symbol):
    """Return the events from Yahoo Finance's Company Event Calendar.

    List of events (represented as dictionaries with keys date, type, url and content) are returned.
    """
    http = Http()
    y = yql.Public(httplib2_inst=http)

    query = 'use "https://raw.githubusercontent.com/tibkiss/yql-tables/yahoo_finance_companyevents/yahoo/finance/yahoo.finance.companyevents.xml" as yahoo.finance.companyevents;' \
            'select * from yahoo.finance.companyevents where symbol = "%s"' % symbol

    log.debug('Executing query: %s', query)
    yres = y.execute(query)
    log.debug('Results: %s', yres.results)

    # We need to explicitly close the associated http connection as pypy is lazy.
    # If not closed we run out of file descriptors
    for key in http.connections:
       http.connections[key].close()

    if 'event' not in yres.results['companyEvents']:
        # Return an empty list if no events were returned
        return []

    events = yres.results['companyEvents']['event']

    if isinstance(events, dict):
        event_list = [events, ]
    elif isinstance(events, list):
        event_list = events
    else:
        raise Exception("YQL returned invalid data")

    result_list = []
    for event in event_list:
        # Convert the date string to date object
        # Date format: 6-May-15
        # Yahoo Finance's Earnings Calender often contains estimated
        # earning dates with the following date format: Jul 22 - Jul 27, 2015 (Est.)
        # We filter out those estimates
        try:
            event['date'] = datetime.strptime(event['date'], '%d-%b-%y').date()
        except ValueError, e:
            # Skip the event with unparsable date (i.e., estimates)
            continue

        result_list.append(DBHandler.yahoo_company_event(event_date=event['date'], symbol=symbol,
                                                         event_type=event['type'], event_content=event['content']))

    return result_list


def get_current_earnings(symbol):
    """Filters the events for 'Earnings announcement' in their content"""
    return [e for e in get_current_events(symbol) if e.event_content.find('Earnings announcement') != -1]


def get_earnings(symbol, start_date, end_date):
    """Filters the earning events for the give date range"""
    return [e for e in get_current_earnings(symbol) if start_date <= e.event_date < end_date]


def store_events_in_db(event_list):
    db_handler = DBHandler(HUBA_DB_URI)

    for event in event_list:
        try:
            db_handler.store_yahoo_company_event(event, commit=True)
        except Exception as e:
            log.error('Exception: %s', str(e))
            log.error('%s', event)

    db_handler.connection.close()


def main(args):
    args = docopt(__doc__, argv=args, version=get_git_version())

    if args['--verbose']:
        log.setLevel(logging.INFO)
        logConsole.setLevel(logging.INFO)

    if args['--debug']:
        log.setLevel(logging.DEBUG)
        logConsole.setLevel(logging.DEBUG)

    if args['get-traded']:
        stocks = get_huba_instruments()
    elif args['get-from-file']:
        stocks = get_instruments_from_txt(args['<filename>'])
    elif args['<stock>']:
        stocks = [args['<stock>'], ]

    for stock in stocks:
        log.info("Downloading events for stock: %s", stock)
        try:
            events = get_current_events(stock)
        except Exception as e:
            log.error('Exception: %s', str(e))
        else:
            if args['--store-in-db']:
                log.info("Storing %d events to DB", len(events))
                store_events_in_db(events)
            else:
                print events

if __name__ == '__main__':
    log = logging.getLogger()
    log.setLevel(logging.WARN)
    logConsole = logging.StreamHandler(sys.stdout)
    logConsole.setLevel(logging.WARN)
    log.addHandler(logConsole)
    main(sys.argv[1:])
