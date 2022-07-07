#!/usr/bin/env python2.7

from matplotlib import pyplot as plt
from pandas import *

r = read_csv('logs/equities-paper.csv', parse_dates=[0])
plt.plot(r['DateTime'], r['Equity'])
plt.ylim([0, 50000])
plt.show()
