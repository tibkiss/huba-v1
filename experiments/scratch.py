__author__ = 'tiborkiss'

from tools.csv_tools import loadHistoricalBars

import datetime
from pyalgotrade.barfeed import Frequency

startDate = datetime.date(2009, 1, 1)
endDate = datetime.date(2012, 12, 31)
%time %memit c = loadHistoricalBars('DIA', startDate, endDate, Frequency.MINUTE)


# Fake trade fill
broker._Broker__ibConnection.orderStatus(130, 'Filled', 64, 0, 42.00, 0, 0, 42.00, 0, 'csak')
