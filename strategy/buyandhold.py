__author__ = 'tiborkiss'

from strategy import Strategy

class BuyAndHoldStrategyParms(object):
    def __init__(self, allocPct, action):
        self.allocPct = allocPct   # Allocation percentage: 0 .. 1
        self.action = action       # Order direction: Order.Action.BUY or Order.Action.SELL


class BuyAndHoldStrategy(Strategy):
    def __init__(self, instr, parms, now, brokerAgent):
        Strategy.__init__(self, instr, brokerAgent, now)

        self._instr = instr
        self._parms = parms
        self._qty = self._broker.getEquity() * self._parms.allocPct

        self._runGuarded(self._initStrategy, )

    def _initStrategy(self):
        qty = self._broker.getShares(self._instr)

        if qty < self._qty[self._instr]:
            order = self._broker.createMarketOrder(self._parms.action, self._instr, abs(self._qty))
            self._broker.placeOrder(order)


    def onBars(self, bar, instrument):
        pass

    def onOrderUpdate(self, order):
        pass

    def stop(self):
        pass