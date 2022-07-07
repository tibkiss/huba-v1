import unittest

from datetime import datetime

import logging
log=logging.getLogger(__name__)

from tools import priceRound, rint, reduceBars, ATR, downscaleBars, downscaleBarsInTime

import pytz

from pyalgotrade.bar import Bar
from pyalgotrade.providers.interactivebrokers.ibbar import Bar as IBBar

class ToolsTestCase(unittest.TestCase):
    def testPriceRound(self):
        for sign in (1.0, -1.0):
            self.assertEquals(priceRound(sign*1.1234567, 2, 0.05), sign*1.10)
            self.assertEquals(priceRound(sign*1.1234567, 2, 0.1), sign*1.1)
            self.assertEquals(priceRound(sign*1.0, 2, 0.1), sign*1.00)
            self.assertEquals(priceRound(sign*1.100000001, 2, 0.1), sign*1.10)
            self.assertEquals(priceRound(sign*1.1234567, 4, 0.05), sign*1.1000)
            self.assertEquals(priceRound(sign*1.123678, 4, 0.05), sign*1.1000)
            self.assertEquals(priceRound(sign*1.123678, 4, 0.0005), sign*1.1235)
            self.assertEquals(priceRound(sign*1.123878, 4, 0.0005), sign*1.1240)

    def testRInt(self):
        self.assertTrue(rint(0.00) == 0)
        self.assertTrue(rint(0.01) == 0)
        self.assertTrue(rint(0.10) == 0)
        self.assertTrue(rint(0.20) == 0)
        self.assertTrue(rint(0.30) == 0)
        self.assertTrue(rint(0.40) == 0)
        self.assertTrue(rint(0.50) == 0)
        self.assertTrue(rint(0.51) == 1)
        self.assertTrue(rint(0.99) == 1)
        self.assertTrue(rint(1.00) == 1)
        self.assertTrue(rint(1.01) == 1)
        self.assertTrue(rint(1.51) == 2)

    def testReduceBars(self):
        # Test with ibbar.Bar and bar.Bar
        ibbars = [IBBar(datetime(2012, 07, 23, 22, 32), open_=11, high=15, low=7, close=12, volume=1, vwap=2, tradeCount=3),
                  IBBar(datetime(2012, 07, 23, 22, 33), open_=12, high=17, low=12, close=13, volume=2, vwap=3, tradeCount=4),
                  IBBar(datetime(2012, 07, 23, 22, 34), open_=8, high=20, low=8, close=20, volume=3, vwap=4, tradeCount=5),
                  IBBar(datetime(2012, 07, 23, 22, 35), open_=21, high=30, low=11, close=21, volume=4, vwap=5, tradeCount=6),
                  IBBar(datetime(2012, 07, 23, 22, 36), open_=22, high=22, low=4, close=12, volume=5, vwap=6, tradeCount=7),
                 ]
        bars = [Bar(datetime(2012, 07, 23, 22, 32), open_=11, high=15, low=7, close=12, volume=1, adjClose=12.1),
                Bar(datetime(2012, 07, 23, 22, 33), open_=12, high=17, low=12, close=13, volume=2, adjClose=13.1),
                Bar(datetime(2012, 07, 23, 22, 34), open_=8, high=20, low=8, close=20, volume=3, adjClose=20.1),
                Bar(datetime(2012, 07, 23, 22, 35), open_=21, high=30, low=11, close=21, volume=4, adjClose=21.1),
                Bar(datetime(2012, 07, 23, 22, 36), open_=22, high=22, low=4, close=12, volume=5, adjClose=12.1),
               ]

        for testBars in (ibbars, bars):
            bar = reduceBars(testBars)

            self.assertIsInstance(bar, Bar)
            self.assertTrue(bar.getDateTime() == datetime(2012, 07, 23, 22, 32))
            self.assertTrue(bar.getOpen() == 11)
            self.assertTrue(bar.getHigh() == 30)
            self.assertTrue(bar.getLow() == 4)
            self.assertTrue(bar.getClose() == 12)
            if testBars == ibbars:
                self.assertTrue(bar.getAdjClose() == bar.getClose())
            else:
                self.assertTrue(bar.getAdjClose() == 12.1)
            self.assertTrue(bar.getVolume() == 1+2+3+4+5)
            # IBBar's VWAP and TradeCount is not included: Bar is returned from reduceBars

    def testDownscaleBars(self):
        # 9 Bars
        bars = [IBBar(datetime(2012, 10, 5, 15, 20,  5), open_=11, high=13, low=10, close=12, volume=100, vwap=1000, tradeCount=1),
                IBBar(datetime(2012, 10, 5, 15, 20, 10), open_=21, high=23, low=20, close=22, volume=200, vwap=2000, tradeCount=2),
                IBBar(datetime(2012, 10, 5, 15, 20, 15), open_=31, high=33, low=30, close=32, volume=300, vwap=3000, tradeCount=3),
                IBBar(datetime(2012, 10, 5, 15, 20, 20), open_=41, high=43, low=40, close=42, volume=400, vwap=4000, tradeCount=4),
                IBBar(datetime(2012, 10, 5, 15, 20, 25), open_=51, high=53, low=50, close=52, volume=500, vwap=5000, tradeCount=5),
                IBBar(datetime(2012, 10, 5, 15, 20, 30), open_=61, high=63, low=60, close=62, volume=600, vwap=6000, tradeCount=6),
                IBBar(datetime(2012, 10, 5, 15, 20, 35), open_=71, high=73, low=70, close=72, volume=700, vwap=7000, tradeCount=7),
                IBBar(datetime(2012, 10, 5, 15, 20, 40), open_=81, high=83, low=80, close=82, volume=800, vwap=8000, tradeCount=8),
                IBBar(datetime(2012, 10, 5, 15, 20, 45), open_=92, high=93, low=90, close=92, volume=900, vwap=9000, tradeCount=9),
               ]

        ds = downscaleBars(bars, ticks=2)
        self.assertTrue(len(ds) == 4)
        self.assertTrue(ds[0].getDateTime() == datetime(2012, 10, 5, 15, 20,  5))
        self.assertTrue(ds[0].getOpen() == 11)
        self.assertTrue(ds[0].getClose() == 22)
        self.assertTrue(ds[0].getHigh() == 23)
        self.assertTrue(ds[0].getLow() == 10)
        self.assertTrue(ds[0].getVolume() == 100+200)
        # VWAP and TradeCount is not included as normal Bar is returned
        self.assertTrue(ds[1].getDateTime() == datetime(2012, 10, 5, 15, 20, 15))
        self.assertTrue(ds[1].getOpen() == 31)
        self.assertTrue(ds[1].getClose() == 42)
        self.assertTrue(ds[1].getHigh() == 43)
        self.assertTrue(ds[1].getLow() == 30)
        self.assertTrue(ds[1].getVolume() == 300+400)
        self.assertTrue(ds[2].getDateTime() == datetime(2012, 10, 5, 15, 20, 25))
        self.assertTrue(ds[2].getOpen() == 51)
        self.assertTrue(ds[2].getClose() == 62)
        self.assertTrue(ds[2].getHigh() == 63)
        self.assertTrue(ds[2].getLow() == 50)
        self.assertTrue(ds[2].getVolume() == 500+600)
        self.assertTrue(ds[3].getDateTime() == datetime(2012, 10, 5, 15, 20, 35))
        self.assertTrue(ds[3].getOpen() == 71)
        self.assertTrue(ds[3].getClose() == 82)
        self.assertTrue(ds[3].getHigh() == 83)
        self.assertTrue(ds[3].getLow() == 70)
        self.assertTrue(ds[3].getVolume() == 700+800)

        ds = downscaleBars(bars, ticks=3)
        self.assertTrue(len(ds) == 3)
        self.assertTrue(ds[0].getDateTime() == datetime(2012, 10, 5, 15, 20,  5))
        self.assertTrue(ds[0].getOpen() == 11)
        self.assertTrue(ds[0].getClose() == 32)
        self.assertTrue(ds[0].getHigh() == 33)
        self.assertTrue(ds[0].getLow() == 10)
        self.assertTrue(ds[0].getVolume() == 100+200+300)
        self.assertTrue(ds[1].getDateTime() == datetime(2012, 10, 5, 15, 20, 20))
        self.assertTrue(ds[1].getOpen() == 41)
        self.assertTrue(ds[1].getClose() == 62)
        self.assertTrue(ds[1].getHigh() == 63)
        self.assertTrue(ds[1].getLow() == 40)
        self.assertTrue(ds[1].getVolume() == 400+500+600)
        self.assertTrue(ds[2].getDateTime() == datetime(2012, 10, 5, 15, 20, 35))
        self.assertTrue(ds[2].getOpen() == 71)
        self.assertTrue(ds[2].getClose() == 92)
        self.assertTrue(ds[2].getHigh() == 93)
        self.assertTrue(ds[2].getLow() == 70)
        self.assertTrue(ds[2].getVolume() == 700+800+900)

        ds = downscaleBars(bars, ticks=4)
        self.assertTrue(len(ds) == 2)
        self.assertTrue(ds[0].getDateTime() == datetime(2012, 10, 5, 15, 20,  5))
        self.assertTrue(ds[0].getOpen() == 11)
        self.assertTrue(ds[0].getClose() == 42)
        self.assertTrue(ds[0].getHigh() == 43)
        self.assertTrue(ds[0].getLow() == 10)
        self.assertTrue(ds[0].getVolume() == 100+200+300+400)
        self.assertTrue(ds[1].getDateTime() == datetime(2012, 10, 5, 15, 20, 25))
        self.assertTrue(ds[1].getOpen() == 51)
        self.assertTrue(ds[1].getClose() == 82)
        self.assertTrue(ds[1].getHigh() == 83)
        self.assertTrue(ds[1].getLow() == 50)
        self.assertTrue(ds[1].getVolume() == 500+600+700+800)

        ds = downscaleBars(bars, ticks=5)
        self.assertTrue(len(ds) == 1)
        self.assertTrue(ds[0].getDateTime() == datetime(2012, 10, 5, 15, 20,  5))
        self.assertTrue(ds[0].getOpen() == 11)
        self.assertTrue(ds[0].getClose() == 52)
        self.assertTrue(ds[0].getHigh() == 53)
        self.assertTrue(ds[0].getLow() == 10)
        self.assertTrue(ds[0].getVolume() == 100+200+300+400+500)

    def testDownscaleBarsInTime(self):
        tz = pytz.utc
        bars = [IBBar(datetime(2012, 10, 5, 4, 18,  5, tzinfo=tz), open_=11, high=13, low=10, close=12, volume=100, vwap=1000, tradeCount=1),
                IBBar(datetime(2012, 10, 5, 4, 18, 10, tzinfo=tz), open_=21, high=23, low=20, close=22, volume=200, vwap=2000, tradeCount=2),

                IBBar(datetime(2012, 10, 5, 4, 19, 15, tzinfo=tz), open_=31, high=33, low=30, close=32, volume=300, vwap=3000, tradeCount=3),
                IBBar(datetime(2012, 10, 5, 4, 19, 20, tzinfo=tz), open_=41, high=43, low=40, close=42, volume=400, vwap=4000, tradeCount=4),

                IBBar(datetime(2012, 10, 5, 4, 20, 00, tzinfo=tz), open_=51, high=53, low=50, close=52, volume=500, vwap=5000, tradeCount=5),

                IBBar(datetime(2012, 10, 6, 2, 10, 30, tzinfo=tz), open_=61, high=63, low=60, close=62, volume=600, vwap=6000, tradeCount=6),
                IBBar(datetime(2012, 10, 6, 2, 10, 35, tzinfo=tz), open_=71, high=73, low=70, close=72, volume=700, vwap=7000, tradeCount=7),
               ]

        ds = downscaleBarsInTime(bars, minutes=1)
        self.assertTrue(len(ds) == 4)
        self.assertTrue(ds[0].getDateTime() == datetime(2012, 10, 5, 4, 18, 0, tzinfo=tz))
        self.assertTrue(ds[0].getOpen() == 11)
        self.assertTrue(ds[0].getClose() == 22)
        self.assertTrue(ds[0].getHigh() == 23)
        self.assertTrue(ds[0].getLow() == 10)
        self.assertTrue(ds[0].getVolume() == 100+200)
        # VWAP and TradeCount is not included as normal Bar is returned

        self.assertTrue(ds[1].getDateTime() == datetime(2012, 10, 5, 4, 19, 0, tzinfo=tz))
        self.assertTrue(ds[1].getOpen() == 31)
        self.assertTrue(ds[1].getClose() == 42)
        self.assertTrue(ds[1].getHigh() == 43)
        self.assertTrue(ds[1].getLow() == 30)
        self.assertTrue(ds[1].getVolume() == 300+400)

        self.assertTrue(ds[2].getDateTime() == datetime(2012, 10, 5, 4, 20, 0, tzinfo=tz))
        self.assertTrue(ds[2].getOpen() == 51)
        self.assertTrue(ds[2].getClose() == 52)
        self.assertTrue(ds[2].getHigh() == 53)
        self.assertTrue(ds[2].getLow() == 50)
        self.assertTrue(ds[2].getVolume() == 500)

        self.assertTrue(ds[3].getDateTime() == datetime(2012, 10, 6, 2, 10, 0, tzinfo=tz))
        self.assertTrue(ds[3].getOpen() == 61)
        self.assertTrue(ds[3].getClose() == 72)
        self.assertTrue(ds[3].getHigh() == 73)
        self.assertTrue(ds[3].getLow() == 60)
        self.assertTrue(ds[3].getVolume() == 600+700)

        ds = downscaleBarsInTime(bars, minutes=5)
        self.assertTrue(len(ds) == 3)
        self.assertTrue(ds[0].getDateTime() == datetime(2012, 10, 5, 4, 15, 0, tzinfo=tz))
        self.assertTrue(ds[0].getOpen() == 11)
        self.assertTrue(ds[0].getClose() == 42)
        self.assertTrue(ds[0].getHigh() == 43)
        self.assertTrue(ds[0].getLow() == 10)
        self.assertTrue(ds[0].getVolume() == 100+200+300+400)

        self.assertTrue(ds[1].getDateTime() == datetime(2012, 10, 5, 4, 20, 0, tzinfo=tz))
        self.assertTrue(ds[1].getOpen() == 51)
        self.assertTrue(ds[1].getClose() == 52)
        self.assertTrue(ds[1].getHigh() == 53)
        self.assertTrue(ds[1].getLow() == 50)
        self.assertTrue(ds[1].getVolume() == 500)

        self.assertTrue(ds[2].getDateTime() == datetime(2012, 10, 6, 2, 10, 0, tzinfo=tz))
        self.assertTrue(ds[2].getOpen() == 61)
        self.assertTrue(ds[2].getClose() == 72)
        self.assertTrue(ds[2].getHigh() == 73)
        self.assertTrue(ds[2].getLow() == 60)
        self.assertTrue(ds[2].getVolume() == 600+700)

        ds = downscaleBarsInTime(bars, minutes=60)
        self.assertTrue(len(ds) == 2)
        self.assertTrue(ds[0].getDateTime() == datetime(2012, 10, 5, 4, 0, 0, tzinfo=tz))
        self.assertTrue(ds[0].getOpen() == 11)
        self.assertTrue(ds[0].getClose() == 52)
        self.assertTrue(ds[0].getHigh() == 53)
        self.assertTrue(ds[0].getLow() == 10)
        self.assertTrue(ds[0].getVolume() == 100+200+300+400+500)

        self.assertTrue(ds[1].getDateTime() == datetime(2012, 10, 6, 2, 0, 0, tzinfo=tz))
        self.assertTrue(ds[1].getOpen() == 61)
        self.assertTrue(ds[1].getClose() == 72)
        self.assertTrue(ds[1].getHigh() == 73)
        self.assertTrue(ds[1].getLow() == 60)
        self.assertTrue(ds[1].getVolume() == 600+700)

        ds = downscaleBarsInTime(bars, minutes=1440)  # Daily
        self.assertTrue(len(ds) == 2)
        self.assertTrue(ds[0].getDateTime() == datetime(2012, 10, 5, 0, 0, 0, tzinfo=tz))
        self.assertTrue(ds[0].getOpen() == 11)
        self.assertTrue(ds[0].getClose() == 52)
        self.assertTrue(ds[0].getHigh() == 53)
        self.assertTrue(ds[0].getLow() == 10)
        self.assertTrue(ds[0].getVolume() == 100+200+300+400+500)

        self.assertTrue(ds[1].getDateTime() == datetime(2012, 10, 6, 0, 0, 0, tzinfo=tz))
        self.assertTrue(ds[1].getOpen() == 61)
        self.assertTrue(ds[1].getClose() == 72)
        self.assertTrue(ds[1].getHigh() == 73)
        self.assertTrue(ds[1].getLow() == 60)
        self.assertTrue(ds[1].getVolume() == 600+700)

    def testATR(self):
        # ATR: http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:average_true_range_atr
        # ,,,High,Low,Close,H - L,I H - Cp I,I L - Cp I,TR,ATR,
        # ,,1-Apr-10,48.70,47.79,48.16,    0.91 ,,,0.91,,
        # ,,5-Apr-10,48.72,48.14,48.61,    0.58 ,0.56,0.02,0.58,,
        # ,,6-Apr-10,48.90,48.39,48.75,    0.51 ,0.29,0.22,0.51,,
        # ,,7-Apr-10,48.87,48.37,48.63,    0.50 ,0.12,0.38,0.50,,
        # ,,8-Apr-10,48.82,48.24,48.74,    0.58 ,0.19,0.39,0.58,,
        # ,,9-Apr-10,49.05,48.64,49.03,    0.41 ,0.31,0.11,0.41,,
        # ,,12-Apr-10,49.20,48.94,49.07,   0.26 ,0.17,0.09,0.26,,
        # ,,13-Apr-10,49.35,48.86,49.32,   0.49 ,0.28,0.21,0.49,,
        # ,,14-Apr-10,49.92,49.50,49.91,   0.42 ,0.60,0.18,0.60,,
        # ,,15-Apr-10,50.19,49.87,50.13,   0.32 ,0.28,0.04,0.32,,
        # ,,16-Apr-10,50.12,49.20,49.53,   0.92 ,0.01,0.93,0.93,,
        # ,,19-Apr-10,49.66,48.90,49.50,   0.76 ,0.13,0.63,0.76,,
        # ,,20-Apr-10,49.88,49.43,49.75,   0.45 ,0.38,0.07,0.45,,
        # ,,21-Apr-10,50.19,49.73,50.03,   0.46 ,0.44,0.02,0.46,0.56,
        # ,1,22-Apr-10,50.36,49.26,50.31,  1.10 ,0.33,0.77,1.10,0.59,
        # ,2,23-Apr-10,50.57,50.09,50.52,  0.48 ,0.26,0.22,0.48,0.59,
        # ,3,26-Apr-10,50.65,50.30,50.41,  0.35 ,0.13,0.22,0.35,0.57,
        # ,4,27-Apr-10,50.43,49.21,49.34,  1.22 ,0.02,1.20,1.22,0.62,
        # ,5,28-Apr-10,49.63,48.98,49.37,  0.65 ,0.29,0.36,0.65,0.62,
        # ,6,29-Apr-10,50.33,49.61,50.23,  0.72 ,0.96,0.24,0.96,0.64,
        # ,7,30-Apr-10,50.29,49.20,49.24,  1.09 ,0.06,1.03,1.09,0.67,
        # ,8,3-May-10,50.17,49.43,49.93,   0.74 ,0.93,0.19,0.93,0.69,
        # ,9,4-May-10,49.32,48.08,48.43,   1.24 ,0.61,1.85,1.85,0.78,
        # ,10,5-May-10,48.50,47.64,48.18,  0.86 ,0.07,0.79,0.86,0.78,
        # ,11,6-May-10,48.32,41.55,46.57,  6.77 ,0.14,6.63,6.77,1.21,
        # ,12,7-May-10,46.80,44.28,45.41,  2.52 ,0.23,2.29,2.52,1.30,
        # ,13,10-May-10,47.80,47.31,47.77, 0.49 ,2.39,1.90,2.39,1.38,
        # ,14,11-May-10,48.39,47.20,47.72, 1.19 ,0.62,0.57,1.19,1.37,
        # ,15,12-May-10,48.66,47.90,48.62, 0.76 ,0.94,0.18,0.94,1.34,
        # ,16,13-May-10,48.79,47.73,47.85, 1.06 ,0.17,0.89,1.06,1.32,
        # Period = 14
        atr = ATR(period=14)
        self.assertTrue(len(atr._trs)  == 0)
        self.assertTrue(len(atr._atrs) == 0)
        atr.onBar(Bar(datetime(2010, 4,  1), 48.70, 48.70, 47.79, 48.16, 100, 0)) # TR=0.91, ATR=None
        self.assertTrue(round(atr._trs[-1], 2) == 0.91)
        self.assertTrue(len(atr._atrs) == 0)
        atr.onBar(Bar(datetime(2010, 4,  5), 48.72, 48.72, 48.14, 48.61, 100, 0)) # TR=0.58, ATR=None
        self.assertTrue(round(atr._trs[-1], 2) == 0.58)
        self.assertTrue(len(atr._atrs) == 0)
        atr.onBar(Bar(datetime(2010, 4,  6), 48.90, 48.90, 48.39, 48.75, 100, 0)) # TR=0.51, ATR=None
        self.assertTrue(round(atr._trs[-1], 2) == 0.51)
        self.assertTrue(len(atr._atrs) == 0)
        atr.onBar(Bar(datetime(2010, 4,  7), 48.87, 48.87, 48.37, 48.63, 100, 0)) # TR=0.50, ATR=None
        self.assertTrue(round(atr._trs[-1], 2) == 0.50)
        self.assertTrue(len(atr._atrs) == 0)
        atr.onBar(Bar(datetime(2010, 4,  8), 48.82, 48.82, 48.24, 48.74, 100, 0)) # TR=0.58, ATR=None
        self.assertTrue(round(atr._trs[-1], 2) == 0.58)
        self.assertTrue(len(atr._atrs) == 0)
        atr.onBar(Bar(datetime(2010, 4,  9), 49.05, 49.05, 48.64, 49.03, 100, 0)) # TR=0.41, ATR=None
        self.assertTrue(round(atr._trs[-1], 2) == 0.41)
        self.assertTrue(len(atr._atrs) == 0)
        atr.onBar(Bar(datetime(2010, 4, 12), 49.20, 49.20, 48.94, 49.07, 100, 0)) # TR=0.26, ATR=None
        self.assertTrue(round(atr._trs[-1], 2) == 0.26)
        self.assertTrue(len(atr._atrs) == 0)
        atr.onBar(Bar(datetime(2010, 4, 13), 49.35, 49.35, 48.86, 49.32, 100, 0)) # TR=0.49, ATR=None
        self.assertTrue(round(atr._trs[-1], 2) == 0.49)
        self.assertTrue(len(atr._atrs) == 0)
        atr.onBar(Bar(datetime(2010, 4, 14), 49.92, 49.92, 49.50, 49.91, 100, 0)) # TR=0.60, ATR=None
        self.assertTrue(round(atr._trs[-1], 2) == 0.60)
        self.assertTrue(len(atr._atrs) == 0)
        atr.onBar(Bar(datetime(2010, 4, 15), 50.19, 50.19, 49.87, 50.13, 100, 0)) # TR=0.32, ATR=None
        self.assertTrue(round(atr._trs[-1], 2) == 0.32)
        self.assertTrue(len(atr._atrs) == 0)
        atr.onBar(Bar(datetime(2010, 4, 16), 50.12, 50.12, 49.20, 49.53, 100, 0)) # TR=0.93, ATR=None
        self.assertTrue(round(atr._trs[-1], 2) == 0.93)
        self.assertTrue(len(atr._atrs) == 0)
        atr.onBar(Bar(datetime(2010, 4, 19), 49.66, 49.66, 48.90, 49.50, 100, 0)) # TR=0.76, ATR=None
        self.assertTrue(round(atr._trs[-1], 2) == 0.76)
        self.assertTrue(len(atr._atrs) == 0)
        atr.onBar(Bar(datetime(2010, 4, 20), 49.88, 49.88, 49.43, 49.75, 100, 0)) # TR=0.45, ATR=None
        self.assertTrue(round(atr._trs[-1], 2) == 0.45)
        self.assertTrue(len(atr._atrs) == 0)
        atr.onBar(Bar(datetime(2010, 4, 21), 50.19, 50.19, 49.73, 50.03, 100, 0)) # TR=0.46, ATR=0.56
        self.assertTrue(round(atr._trs[-1], 2) == 0.46)
        self.assertTrue(round(atr._atrs[-1], 3) == 0.554)
        atr.onBar(Bar(datetime(2010, 4, 22), 50.36, 50.36, 49.26, 50.31, 100, 0)) # TR=1.10, ATR=0.59
        self.assertTrue(round(atr._trs[-1], 2) == 1.10)
        self.assertTrue(round(atr._atrs[-1], 3) == 0.593)
        atr.onBar(Bar(datetime(2010, 4, 23), 50.57, 50.57, 50.09, 50.52, 100, 0)) # TR=0.48, ATR=0.59
        self.assertTrue(round(atr._trs[-1], 2) == 0.48)
        self.assertTrue(round(atr._atrs[-1], 3) == 0.585)
        atr.onBar(Bar(datetime(2010, 4, 26), 50.65, 50.65, 50.30, 50.41, 100, 0)) # TR=0.35, ATR=0.57
        self.assertTrue(round(atr._trs[-1], 2) == 0.35)
        self.assertTrue(round(atr._atrs[-1], 3) == 0.568)
        atr.onBar(Bar(datetime(2010, 4, 27), 50.43, 50.43, 49.21, 49.34, 100, 0)) # TR=1.22, ATR=0.62
        self.assertTrue(round(atr._trs[-1], 2) == 1.22)
        self.assertTrue(round(atr._atrs[-1], 3) == 0.615)
        atr.onBar(Bar(datetime(2010, 4, 28), 49.63, 49.63, 48.98, 49.37, 100, 0)) # TR=0.65, ATR=0.62
        self.assertTrue(round(atr._trs[-1], 2) == 0.65)
        self.assertTrue(round(atr._atrs[-1], 3) == 0.617)
        atr.onBar(Bar(datetime(2010, 4, 29), 50.33, 50.33, 49.61, 50.23, 100, 0)) # TR=0.96, ATR=0.64
        self.assertTrue(round(atr._trs[-1], 2) == 0.96)
        self.assertTrue(round(atr._atrs[-1], 3) == 0.642)
        atr.onBar(Bar(datetime(2010, 4, 30), 50.29, 50.29, 49.20, 49.24, 100, 0)) # TR=1.09, ATR=0.67
        self.assertTrue(round(atr._trs[-1], 2) == 1.09)
        self.assertTrue(round(atr._atrs[-1], 3) == 0.674)
        atr.onBar(Bar(datetime(2010, 5,  3), 50.17, 50.17, 49.43, 49.93, 100, 0)) # TR=0.93, ATR=0.69
        self.assertTrue(round(atr._trs[-1], 2) == 0.93)
        self.assertTrue(round(atr._atrs[-1], 3) == 0.692)
        atr.onBar(Bar(datetime(2010, 5,  4), 49.32, 49.32, 48.08, 48.43, 100, 0)) # TR=1.85, ATR=0.78
        self.assertTrue(round(atr._trs[-1], 2) == 1.85)
        self.assertTrue(round(atr._atrs[-1], 3) == 0.775)
        atr.onBar(Bar(datetime(2010, 5,  5), 48.50, 48.50, 47.64, 48.18, 100, 0)) # TR=0.86, ATR=0.78
        self.assertTrue(round(atr._trs[-1], 2) == 0.86)
        self.assertTrue(round(atr._atrs[-1], 3) == 0.781)
        atr.onBar(Bar(datetime(2010, 5,  6), 48.32, 48.32, 41.55, 46.57, 100, 0)) # TR=6.77, ATR=1.21
        self.assertTrue(round(atr._trs[-1], 2) == 6.77)
        self.assertTrue(round(atr._atrs[-1], 3) == 1.209)
        atr.onBar(Bar(datetime(2010, 5,  7), 46.80, 46.80, 44.28, 45.41, 100, 0)) # TR=2.52, ATR=1.30
        self.assertTrue(round(atr._trs[-1], 2) == 2.52)
        self.assertTrue(round(atr._atrs[-1], 3) == 1.302)
        atr.onBar(Bar(datetime(2010, 5, 10), 47.80, 47.80, 47.31, 47.77, 100, 0)) # TR=2.39, ATR=1.38
        self.assertTrue(round(atr._trs[-1], 2) == 2.39)
        self.assertTrue(round(atr._atrs[-1], 3) == 1.380)
        atr.onBar(Bar(datetime(2010, 5, 11), 48.39, 48.39, 47.20, 47.72, 100, 0)) # TR=1.19, ATR=1.37
        self.assertTrue(round(atr._trs[-1], 2) == 1.19)
        self.assertTrue(round(atr._atrs[-1], 3) == 1.367)
        atr.onBar(Bar(datetime(2010, 5, 12), 48.66, 48.66, 47.90, 48.62, 100, 0)) # TR=0.94, ATR=1.34
        self.assertTrue(round(atr._trs[-1], 2) == 0.94)
        self.assertTrue(round(atr._atrs[-1], 3) == 1.336)
        atr.onBar(Bar(datetime(2010, 5, 13), 48.79, 48.79, 47.73, 47.85, 100, 0)) # TR=1.06, ATR=1.32
        self.assertTrue(round(atr._trs[-1], 2) == 1.06)
        self.assertTrue(round(atr._atrs[-1], 3) == 1.316)
