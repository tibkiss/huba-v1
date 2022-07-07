import unittest

import logging
log=logging.getLogger(__name__)

from strategy.riskmanager import RiskManager, MIN_QTY

from mock import sentinel
import random

class RiskManagerTestCase(unittest.TestCase):
    def testSequence(self):
        leverage = 1.5
        maxPositionCount = 2
        instrPerPosition = 2
        tradeCapital = 10000
        rm = RiskManager(tradeCapital, leverage, maxPositionCount, instrPerPosition)

        # Verify that the variables are set
        self.assertTrue(rm._tradeCapital == tradeCapital)
        self.assertTrue(rm._leverage == leverage)
        self.assertTrue(rm._maxPositionCount == maxPositionCount)
        self.assertTrue(rm._instrPerPosition == instrPerPosition)

        # Try to set the capital
        rm.setTradeCapital(15000)
        self.assertTrue(rm.getTradeCapital() == 15000)
        rm.setTradeCapital(10000)
        self.assertTrue(rm.getTradeCapital() == 10000)
        tradeCapital = rm.getTradeCapital()

        # Try to remove nonexistent position, should raise error
        self.assertRaises(ValueError, rm.removePosition,
                          (sentinel._instrument0, sentinel._instrument1))

        self.assertTrue(len(rm._positions) == 0)

        # Add one existing position
        qty = rm.addPosition((sentinel.instrument0, sentinel.instrument1))
        self.assertTrue(qty is None) # No quantity should be returned if no price given

        # Should be included in the _positions
        self.assertTrue(len(rm._positions) == 1)

        # Try to add it again, should not change the size of _positions
        qty = rm.addPosition((sentinel.instrument0, sentinel.instrument1), price=10.2)
        # Maximal allocatable capital per instrument is: 10000/4*1.5=3750
        # Qty per instrument: 3750/10.2=367
        self.assertTrue(qty == 367)

        # The size of _positions should not change
        self.assertTrue(len(rm._positions) == 1)

        # Try to add a second position, with price
        qty = rm.addPosition((sentinel.instrument1, sentinel.instrument2), price=7)
        # 4 stocks registered with the $10k trade capital and leverage of 1
        # Maximal allocatable capital per instrument is: 10000/4*1.5=3750
        # Quantity per instrument is 3750/7=535
        self.assertTrue(qty == 535)

        # Should be added to the positions
        self.assertTrue(len(rm._positions) == 2)

        # Try to add third position, will not fit
        self.assertRaises(ValueError, rm.addPosition,
                          ((sentinel.instrument4, sentinel.instrument5), 4))

        # Should not be added to the positions
        self.assertTrue(len(rm._positions) == 2)

        # Try to remove existing position
        rm.removePosition((sentinel.instrument0, sentinel.instrument1))

        # Should be removed from the positions
        self.assertTrue(len(rm._positions) == 1)

        # Try to increase the trade capital
        rm.setTradeCapital(50000)
        self.assertTrue(rm.getTradeCapital() == 50000)

        # Try to add a new position with price
        qty = rm.addPosition((sentinel.instrument4, sentinel.instrument5), price=12.4)
        # Maximal allocatable capital per instrument is: 50000/4*1.5=18750
        # Qty per instrument: 18750/12.4=1512
        self.assertTrue(qty == 1512)

        # Try to remove all positions
        rm.removePosition((sentinel.instrument1, sentinel.instrument2))
        rm.removePosition((sentinel.instrument4, sentinel.instrument5))

        # Set should be empty
        self.assertTrue(len(rm._positions) == 0)

        # Trying to remove nonexistent position should raise ValueError
        self.assertRaises(ValueError, rm.removePosition,
                          ((sentinel.instrument4, sentinel.instrument5)))


        # Create a transaction where the returned qty lower than the minimal quantity
        price = ((rm.getTradeCapital() * leverage)/ (maxPositionCount * instrPerPosition)) / (MIN_QTY - 1)
        self.assertRaises(ValueError, rm.addPosition,
                          (sentinel.instrument6, sentinel.instrument7), price)



def getTestCases():
    ret = [RiskManagerTestCase(e)
           for e in RiskManagerTestCase.__dict__
           if e.startswith('test')]

    return ret