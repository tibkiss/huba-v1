import unittest

import logging
log=logging.getLogger(__name__)

from datetime import datetime, timedelta
from random import randint

from tools.workdays import add_workdays

def random_date(start, end):
    return start + timedelta(
        seconds=randint(0, int((end - start).total_seconds())))


def workdaycount(first, second, inc = 0):
   if first == second:
      return 0
   import math
   if first > second:
      first, second = second, first
   if inc:
      from datetime import timedelta
      second += timedelta(days=1)
   interval = (second - first).days
   weekspan = int(math.ceil(interval / 7.0))
   if interval % 7 == 0:
      return interval - weekspan * 2
   else:
      wdf = first.weekday()
      if (wdf < 6) and ((interval + wdf) // 7 == weekspan):
         modifier = 0
      elif (wdf == 6) or ((interval + wdf + 1) // 7 == weekspan):
         modifier = 1
      else:
         modifier = 2
      return interval - (2 * weekspan - modifier)


class BusinessDaysTestCase(unittest.TestCase):
    def testAddWorkdayStatic(self):
        startDate = datetime(2014, 6, 8)  # Sunday

        return
        self.assertTrue(add_workdays(startDate, 0)  == datetime(2014, 6, 8))   # 0 days ago: same day as startDate
        self.assertTrue(add_workdays(startDate, -1) == datetime(2014, 6, 6))  # 1 days ago: this Thursday
        self.assertTrue(add_workdays(startDate, -2) == datetime(2014, 6, 5))  # 2 days ago: this Wednesday
        self.assertTrue(add_workdays(startDate, -3) == datetime(2014, 6, 4))  # 3 days ago: this Tuesday
        self.assertTrue(add_workdays(startDate, -4) == datetime(2014, 6, 3))  # 4 days ago: this Monday
        self.assertTrue(add_workdays(startDate, -5) == datetime(2014, 5, 30)) # 5 days ago: prev Friday

        self.assertTrue(add_workdays(startDate, -6) == datetime(2014, 5, 29)) # 6 days ago: prev Thursday
        self.assertTrue(add_workdays(startDate, -7) == datetime(2014, 5, 28)) # 7 days ago: prev Wednesday
        self.assertTrue(add_workdays(startDate, -8) == datetime(2014, 5, 27)) # 8 days ago: prev Wednesday
        self.assertTrue(add_workdays(startDate, -9) == datetime(2014, 5, 26)) # 9 days ago: prev Tuesday

        self.assertTrue(add_workdays(startDate, -10) == datetime(2014, 5, 23))
        self.assertTrue(add_workdays(startDate, -11) == datetime(2014, 5, 22))
        self.assertTrue(add_workdays(startDate, -12) == datetime(2014, 5, 21))
        self.assertTrue(add_workdays(startDate, -13) == datetime(2014, 5, 20))
        self.assertTrue(add_workdays(startDate, -14) == datetime(2014, 5, 19))

        self.assertTrue(add_workdays(startDate, -15) == datetime(2014, 5, 16))
        self.assertTrue(add_workdays(startDate, -16) == datetime(2014, 5, 15))
        self.assertTrue(add_workdays(startDate, -17) == datetime(2014, 5, 14))
        self.assertTrue(add_workdays(startDate, -18) == datetime(2014, 5, 13))
        self.assertTrue(add_workdays(startDate, -19) == datetime(2014, 5, 12))

        self.assertTrue(add_workdays(startDate, -20) == datetime(2014, 5, 9))
        self.assertTrue(add_workdays(startDate, -21) == datetime(2014, 5, 8))
        self.assertTrue(add_workdays(startDate, -22) == datetime(2014, 5, 7))
        self.assertTrue(add_workdays(startDate, -23) == datetime(2014, 5, 6))
        self.assertTrue(add_workdays(startDate, -24) == datetime(2014, 5, 5))

        self.assertTrue(add_workdays(startDate, -25) == datetime(2014, 5, 2))
        self.assertTrue(add_workdays(startDate, -26) == datetime(2014, 5, 1))
        self.assertTrue(add_workdays(startDate, -27) == datetime(2014, 4, 30))
        self.assertTrue(add_workdays(startDate, -28) == datetime(2014, 4, 29))
        self.assertTrue(add_workdays(startDate, -29) == datetime(2014, 4, 28))

        self.assertTrue(add_workdays(startDate, -30) == datetime(2014, 4, 25))
        self.assertTrue(add_workdays(startDate, -31) == datetime(2014, 4, 24))
        self.assertTrue(add_workdays(startDate, -32) == datetime(2014, 4, 23))
        self.assertTrue(add_workdays(startDate, -33) == datetime(2014, 4, 22))
        self.assertTrue(add_workdays(startDate, -34) == datetime(2014, 4, 21))

        self.assertTrue(add_workdays(startDate, -35) == datetime(2014, 4, 18))
        self.assertTrue(add_workdays(startDate, -36) == datetime(2014, 4, 17))
        self.assertTrue(add_workdays(startDate, -37) == datetime(2014, 4, 16))
        self.assertTrue(add_workdays(startDate, -38) == datetime(2014, 4, 15))
        self.assertTrue(add_workdays(startDate, -39) == datetime(2014, 4, 14))

        self.assertTrue(add_workdays(startDate, -40) == datetime(2014, 4, 11))
        self.assertTrue(add_workdays(startDate, -41) == datetime(2014, 4, 10))
        self.assertTrue(add_workdays(startDate, -42) == datetime(2014, 4, 9))
        self.assertTrue(add_workdays(startDate, -43) == datetime(2014, 4, 8))
        self.assertTrue(add_workdays(startDate, -44) == datetime(2014, 4, 7))


    def testAddWorkdayRandom(self):
        for i in range(0, 10000):
            startDate = random_date(datetime(2000, 1, 1), datetime(2014, 10, 14))
            daysToadd_workdays = randint(0, 1000)
            endDate = add_workdays(startDate, daysToadd_workdays * -1)

            businessDayCount = workdaycount(startDate, endDate, inc=0)

            self.assertTrue(businessDayCount == daysToadd_workdays)
