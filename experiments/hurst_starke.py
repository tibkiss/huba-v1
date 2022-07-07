#import matplotlib.pyplot as py
from numpy import *


def hurst(p):
    tau = []; lagvec = []
    #  Step through the different lags
    for lag in range(2, 20):
        #  produce price difference with lag
        pp = subtract(p[lag:],p[:-lag])
        #  Write the different lags into a vector
        lagvec.append(lag)
        #  Calculate the variance of the differnce vector
        tau.append(sqrt(std(pp)))
    #  linear fit to double-log graph (gives power)
    m = polyfit(log10(lagvec),log10(tau),1)
    # calculate hurst
    hurst = m[0]*2
    # plot lag vs variance
    #py.plot(lagvec,tau,'o'); show()
    return hurst

if __name__=="__main__":
    #  Different types of time series for testing
    #p = log10(cumsum(random.randn(50000)+1)+1000) # trending, hurst ~ 1
    #p = log10((random.randn(50000))+1000)   # mean reverting, hurst ~ 0
    p = log10(cumsum(random.randn(50000))+1000) # random walk, hurst ~ 0.5
    print hurst(p)