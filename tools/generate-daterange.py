#!/bin/env python2.7

from dateutil.relativedelta import *
from dateutil.easter import *
from dateutil.rrule import *
from dateutil.parser import *
from datetime import *

from business_days import nyse_holidays


set = rruleset()
set.rrule(rrule(DAILY, dtstart=parse("20000102"), until=parse("20130320"), byweekday=(MO, TU, WE, TH, FR)))
for day in nyse_holidays:
    set.exdate(day)

print "Date,Symbol"
for day in list(set):
    print '%04d/%02d/%02d,SPY' % (day.year, day.month, day.day)
