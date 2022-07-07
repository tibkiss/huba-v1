__author__ = 'tiborkiss'

import matplotlib.pyplot as plt
from matplotlib import cm
import pandas as pd
import numpy as np

res = pd.DataFrame()
for i in range(1, 5):
    c = pd.read_csv('backtest-PoolWorker-%d.csv' % i)
    res = res.append(c)

x = res.EntryZScore
x = res.lookbackWindow
y = res.Sharpe

plt.hexbin(x, y, gridsize=30, cmap=cm.jet, bins=None)
plt.axis([x.min(), x.max(), y.min(), y.max()])

cb = plt.colorbar()
cb.set_label('mean value')
plt.show()

for var in ('Sharpe', 'MaxDD', 'DDDur', 'CAGR'):
    for parm in ('EntryZScore', 'lookbackWindow'):
        vals = res[parm].unique()
        for val in vals:
            mean = np.mean(res[res[parm] == val][var])
            print 'Mean %s if %s=%s: %.2f' % (var, parm, val,mean)



pairs = res.Pairs.unique()
for var in ('Sharpe', 'MaxDD', 'DDDur', 'CAGR'):
    for pair in pairs:
        mean = np.mean(res[res.Pairs == pair][var])
        print '%s mean %s: %.2f' % (pair, var, mean)
