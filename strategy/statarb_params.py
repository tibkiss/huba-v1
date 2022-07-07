
from collections import namedtuple


"""Statistical Arbitrage Strategy Parameters:
    lookbackWindow:     Number of days of historical data to take for the hedge ratio calculation
    entryZScore:        Entry threshold: number of standard deviations to enter the trade. Range of 1.0 - 2.0 is normal.
                        Smaller number yields to more frequent trades.
    exitZScore:         Exit threshold: number of standard deviatios to exit the trade. Set to 0 for the sake of symmetry
    zScoreUpdateBuffer: The number of bars to accumulate data before re-evaluating the z-score and decide on trade
                        Used as a simple filter to smooth prices.
    earningsCeaseFire:  Number of days before and after earnings announcement while the trading is not allowed.
                        First number should be minus. If set to False the earnings will not be suspended.
    entryOrderDistance: This variable sets the distance in percents (-1 .. 1) of the limit order for entering the trades.
                        If set to None or False then MarketOrders will be used to enter the position.
    exitOrderDistance:  This variable sets the distance in percents (-1 .. 1) of the limit order for exiting the trades.
                        If set to None or False then MarketOrders will be used to enter the position.
"""
StatArbParams = namedtuple('StatArbParams', ['lookbackWindow',
                                             'entryZScore', 'exitZScore', 'zScoreUpdateBuffer',
                                             'kalmanFilterDelta',
                                             'earningsCeaseFire',
                                             'logPrices', 'hurstEnabled', 'adfullerEnabled',
                                             'entryOrderDistance', 'exitOrderDistance',
                                             'limitPriceIncrements'
                                             ])
StatArbParams.__new__.__defaults__ = (                # Setting default values:
                                      60,             # - lookbackWindow
                                      1.0, 0.0, 2,    # - entryZScore, exitZScore, zScoreUpdateBuffer
                                      0.0001,         # - kalmanFilterDelta
                                      False,          # - earningsCeaseFire
                                      False,          # - logPrices
                                      False,          # - hurstEnabled
                                      False,          # - adfullerEnabled
                                      0.005,          # - entryOrderDistance
                                      0.005,          # - exitOrderDistance
                                      (None, None)    # - limitPriceIncrements
                                     )
