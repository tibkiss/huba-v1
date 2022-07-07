import unittest

import os
from datetime import datetime, date

import logging
log = logging.getLogger(__name__)

import pytz

from mock import Mock, MagicMock, patch, sentinel, call
from tools.csv_tools import writeBarsToNTCSV, loadHistoricalBars, alignBarlist

from pyalgotrade.bar import Bar
from pyalgotrade.barfeed import Frequency
from pyalgotrade.providers.interactivebrokers import ibconnection


class CSVToolsTestCase(unittest.TestCase):
    def setUp(self):
        self.bars = [ Bar(datetime(2001, 1, 1, 2, 2, 2), 11.0, 13.0, 10.0, 12.0, 14.0, 15.0),
                      Bar(datetime(2001, 12, 31, 15, 59, 55), 101.0, 103.0, 100.0, 102.0, 104.0, 105.0),
                      Bar(datetime(2002, 1, 2, 4, 6, 8), 21.0, 23.0, 20.0, 22.0, 24.0, 25.0),
                      Bar(datetime(2002, 12, 31, 15, 59, 55), 201.0, 203.0, 200.0, 202.0, 204.0, 205.0),
                      Bar(datetime(2003, 1, 3, 3, 5, 7), 31.0, 33.0, 30.0, 32.0, 34.0, 35.0),
                      Bar(datetime(2003, 12, 31, 15, 59, 55), 301.0, 303.0, 300.0, 302.0, 304.0, 305.0) ]

    def testDownloadCSV(self):
        pass


    def testLoadHistoricalBars(self):
        instrument = 'FOO'
        startDate = date(2001, 4, 20)
        endDate = date(2003, 4, 20)
        ibConnection = Mock(spec=ibconnection.Connection)
        cacheDir = "testcases/.csvCache"

        # Try to load non-cached data, remove existing files
        # for year in (2001, 2002, 2003):
        #     filename = "%s/HC-%s-%d.csv" % (cacheDir, instrument, year)
        #     if os.path.exists(filename):
        #         os.remove(filename)
        #
        # # Prepare mock results for the ibdownloader.get_historical_data_year
        # bar2001_1, bar2001_2 = Bar(datetime(2001, 1, 1, 2, 2, 2), 11.0, 13.0, 10.0, 12.0, 14.0, 15.0), \
        #                        Bar(datetime(2001, 12, 31, 15, 59, 55), 101.0, 103.0, 100.0, 102.0, 104.0, 105.0)
        # bar2002_1, bar2002_2 = Bar(datetime(2002, 1, 2, 4, 6, 8), 21.0, 23.0, 20.0, 22.0, 24.0, 25.0), \
        #                        Bar(datetime(2002, 12, 31, 15, 59, 55), 201.0, 203.0, 200.0, 202.0, 204.0, 205.0)
        # bar2003_1, bar2003_2 = Bar(datetime(2003, 1, 3, 3, 5, 7), 31.0, 33.0, 30.0, 32.0, 34.0, 35.0), \
        #                        Bar(datetime(2003, 12, 31, 15, 59, 55), 301.0, 303.0, 300.0, 302.0, 304.0, 305.0)
        #
        # # Since the CSV is cached in a local filesystem we cannot check for the Bar instances,
        # # we need to check their contents. Since pyalgotrade adds time zone information, we need to strip that.
        # # The Adjusted Close is not present in the NT CSV Format, thus that is avoided.
        # cmpBars = lambda a, b: (a.getDateTime().replace(tzinfo=pytz.UTC) == b.getDateTime().replace(tzinfo=pytz.UTC) and
        #                         a.getOpen() == b.getOpen() and a.getClose() == b.getClose() and
        #                         a.getLow() == b.getLow() and a.getHigh() == b.getHigh() and
        #                         a.getVolume() == b.getVolume())
        #
        # # Call the routine
        # with patch('pyalgotrade.tools.yahoofinance.get_daily_csv') as MockFct:
        #     MockFct.side_effect = [ [bar2001_1, bar2001_2], [bar2002_1, bar2002_2], [bar2003_1, bar2003_2] ]
        #     bars = loadHistoricalBars(instrument, startDate, endDate, frequency=Frequency.DAY, cacheDir=cacheDir)
        #
        #     # Validate calls
        #     MockFct.assert_any_call(instrument, 2001)
        #     MockFct.assert_any_call(instrument, 2002)
        #     MockFct.assert_any_call(instrument, 2003)
        #
        #     # The first and last bar should not be included due to the startDate - endDate range
        #     self.assertTrue(cmpBars(bars[0], bar2001_2))
        #     self.assertTrue(cmpBars(bars[1], bar2002_1))
        #     self.assertTrue(cmpBars(bars[2], bar2002_2))
        #     self.assertTrue(cmpBars(bars[3], bar2003_1))
        #     self.assertTrue(len(bars) == 4)
        #
        # # Try to load the now cached data
        # with patch('pyalgotrade.tools.yahoofinance.get_daily_csv') as MockFct:
        #     MockFct.return_value = None  # Should not be called anyway
        #     bars = loadHistoricalBars(instrument, startDate, endDate, ibConnection, cacheDir)
        #
        #     self.assertFalse(MockFct.called)
        #     self.assertTrue(cmpBars(bars[0], bar2001_2))
        #     self.assertTrue(cmpBars(bars[1], bar2002_1))
        #     self.assertTrue(cmpBars(bars[2], bar2002_2))
        #     self.assertTrue(cmpBars(bars[3], bar2003_1))
        #     self.assertTrue(len(bars) == 4)


    def testAlignBarlist(self):
        b1, b2 = Bar(datetime(2001, 1, 1, 2, 2, 2), 11, 13, 10, 12, 14, 15), Bar(datetime(2001, 1, 1, 2, 2, 2), 101, 103, 100, 102, 104, 105)
        b3, b4 = Bar(datetime(2002, 1, 2, 4, 6, 8), 21, 23, 20, 22, 24, 25), Bar(datetime(2002, 1, 2, 4, 6, 8), 201, 203, 200, 202, 204, 205)
        b5, b6 = Bar(datetime(2003, 1, 3, 3, 5, 7), 31, 33, 30, 32, 34, 35), Bar(datetime(2003, 1, 3, 3, 5, 7), 301, 303, 300, 302, 304, 305)

        # Check if all the times are matching
        barList1 = [b1, b3, b5]
        barList2 = [b2, b4, b6]
        res1, res2 = alignBarlist(barList1, barList2)
        self.assertTrue(res1 == barList1)
        self.assertTrue(res2 == barList2)

        # Check for partial list
        barList1 = [b1, b3, b5]
        barList2 = [b2, b6]
        res1, res2 = alignBarlist(barList1, barList2)
        self.assertTrue(res1 == [b1, b5])
        self.assertTrue(res2 == [b2, b6])

        barList1 = [b3, b5]
        barList2 = [b2, b4, b6]
        res1, res2 = alignBarlist(barList1, barList2)
        self.assertTrue(res1 == [b3, b5])
        self.assertTrue(res2 == [b4, b6])

        # One of the list is empty
        barList1 = []
        barList2 = [b2, b4, b6]
        res1, res2 = alignBarlist(barList1, barList2)
        self.assertTrue(res1 == [])
        self.assertTrue(res2 == [])

        barList1 = [b1]
        barList2 = []
        res1, res2 = alignBarlist(barList1, barList2)
        self.assertTrue(res1 == [])
        self.assertTrue(res2 == [])
