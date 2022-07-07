#!/usr/bin/env python2.7
"""iqfeed: Data downloader for Iqfeed/DTN
      Tibor Kiss <tibor.kiss@gmail.com> - Copyright (c) 2012-2014 All rights reserved

Usage:
  iqfeed.py get-traded <startyear> <endyear> [-v]
  iqfeed.py get-from-file <filename> <startyear> <endyear>
  iqfeed.py <stock> <startyear> <endyear> [-v]
  iqfeed.py -h | --help

Commands:
  get-trdade        Load the pairs from huba config
  get-from-file     Download symbols listed in the file
Options:
  -v               Verbose mode
  -h               Help screen

"""

import sys, os
import socket
from datetime import datetime
import pytz

import logging
log = logging.getLogger(__name__)

from tools import PYALGOTRADE_PATH
sys.path.append(PYALGOTRADE_PATH)

from tools import CSV_CACHE_DIR
from tools import get_huba_instruments, get_instruments_from_txt
from tools import get_git_version
from tools import retry
from tools.docopt import docopt

from pyalgotrade.bar import Bar

IQFEED_HOST = '127.0.0.1'
IQFEED_PORT = 9100

EasternTZ = pytz.timezone('US/Eastern')

def __read_historical_data_socket(sock, recv_buffer=65535):
    """
    Read the information from the socket, in a buffered
    fashion, receiving only 65535 bytes at a time.

    Parameters:
    sock - The socket object
    recv_buffer - Amount in bytes to receive per read
    """
    buffer = ""
    data = ""

    data = sock.recv(recv_buffer)
    if data.startswith('E,'):  # Error condition
        raise Exception(data)
    buffer += data

    while True:
        data = sock.recv(recv_buffer)
        #print 'new block', " ".join("{:02x}".format(ord(c)) for c in data[-12:])

        buffer += data

        # Check if the end message string arrives
        if buffer.endswith('\n!ENDMSG!,\r\n'):
            break

    # Remove the end message string
    buffer = buffer[:-12]

    # Cut off CR
    buffer = buffer.replace('\r', '')

    return buffer


def download_iqfeed(symbol, beginDate, endDate):
    # IQFeed accepts messages in the following format:
    #   CMD,SYM,[options]\n.
    # Notice the newline character. This must be added otherwise the message will not work.
    # The provided options are
    #   [bars in seconds],[beginning date: CCYYMMDD HHmmSS],[ending date: CCYYMMDD HHmmSS],[empty],
    #   [beginning time filter: HHmmSS],[ending time filter: HHmmSS],[old or new: 0 or 1],[empty],
    #   [queue data points per second].
    # https://github.com/bwlewis/iqfeed/blob/master/man/HIT.Rd
    bars_in_second = 60  # 1M data
    begin_time_filter = '092900'
    end_time_filter = '155900'
    message = "HIT,%s,%s,%s,%s,,%s,%s,1\n" % (symbol, bars_in_second, beginDate, endDate,
                                              begin_time_filter, end_time_filter)

    log.debug("IQFeed request: %s", message.rstrip())

    # print message
    # Open a streaming socket to the IQFeed server locally
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((IQFEED_HOST, IQFEED_PORT))
    sock.settimeout(5.0)

    # Send the historical data request
    # message and buffer the data
    sock.sendall(message)
    data = __read_historical_data_socket(sock)
    sock.close()

    bars = []
    for line in data.split('\n'):
        # print len(line), line

        # Returned fields in data are:
        # DateTime, High, Low, Open, Close, Volume, XXX?
        (dtStr, high, low, open_, close, volume, _, _) = line.split(',')
        if volume.find('.') != -1:
            raise Exception("Float as a volume, strange!: %s" % line)

        # print dtStr, high, low, open_, close, volume
        dt = datetime.strptime(dtStr, "%Y-%m-%d %H:%M:%S")
        dt = EasternTZ.localize(dt)
        (open_, high, low, close, volume) = (float(open_), float(high), float(low), float(close), int(volume))
        adjClose = close
        bar = Bar(dt, float(open_), float(high), float(low), float(close), int(volume), float(adjClose))
        bars.append(bar)

    return bars


def get_1m_bars_for_year(symbol, year):
    beginDate = "%s0101" % year
    endDate = "%s1231" % year
    return download_iqfeed(symbol, beginDate, endDate)


def main(args):
    args = docopt(__doc__, argv=args, version=get_git_version())

    if args['get-traded']:
        stocks = get_huba_instruments()
    elif args['get-from-file']:
        stocks = get_instruments_from_txt(args['<filename>'])
    else:
        stocks = (args['<stock>'], )

    beginYear = int(args['<startyear>'])
    endYear = int(args['<endyear>'])

    # Attach retry decorator to downloader
    get_bars = retry(tries=5, delay=3)(get_1m_bars_for_year)
    #get_bars = get_1m_bars_for_year

    # These imports cannot be done on top as csv_tools are also importing us :S
    from tools.csv_tools import writeBarsToNTCSV

    for (i, symbol) in enumerate(stocks):
        try:
            log.info("Processing %s %d out of %d", symbol, i, len(stocks))

            for year in range(beginYear, endYear+1):
                # Store stock in huba's yearly file
                filename = '%s/HC-%s-1M-%d-iqfeed.csv.gz' % (CSV_CACHE_DIR, symbol, year)

                if False and os.path.exists(filename):
                    log.info('File already exists: %s', filename)
                    continue

                log.info("Downloading to %s", filename)
                bars = get_bars(symbol, year)

                writeBarsToNTCSV(bars, filename, append=False)

        except Exception as e:
            # Just report exception, do not bail
            log.error('Exception!', exc_info=e)


if __name__ == '__main__':
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    logConsole = logging.StreamHandler(sys.stdout)
    logConsole.setLevel(logging.INFO)
    log.addHandler(logConsole)
    main(sys.argv[1:])
