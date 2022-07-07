import unittest

import logging
log=logging.getLogger(__name__)

from pyalgotrade.broker import Broker

from datetime import datetime

from strategy import Strategy
from strategy.brokeragent import BrokerAgent

from mock import Mock, MagicMock, sentinel, patch

class Strategy_Test(unittest.TestCase):
    def setUp(self):
        self._symbols = 'FOO_BAR'
        self._broker = Mock(spec_set=Broker)
        self._ba = Mock(spec=BrokerAgent)
        self._ba.getBroker.return_value = self._broker
        self._now = datetime(2013, 11, 2, 10, 25, 42)

        self._s = Strategy(self._symbols, self._ba, self._now, )

    def testGuarded(self):
        # Check if alive is set correctly after constructing
        self.assertTrue(self._s.alive)

        # Function with no input parameter
        fct = Mock()
        fct.return_value = sentinel.ret
        val = self._s._runGuarded(fct)
        fct.assert_called_once_with()
        self.assertTrue(self._s.alive)
        self.assertTrue(val == sentinel.ret)

        # Input parameters: *args and **kwargs
        fct.reset_mock()
        val = self._s._runGuarded(fct, 12, 20, foo='bar')
        fct.assert_called_once_with(12, 20, foo='bar')
        self.assertTrue(self._s.alive)
        self.assertTrue(val != None)

        # Input parameters: **kwargs only
        fct.reset_mock()
        self._s._runGuarded(fct, bar='baz')
        val = fct.assert_called_once_with(bar='baz')
        self.assertTrue(self._s.alive)
        self.assertTrue(val == None)

        # Returning values
        fct2 = lambda e, f: e+f
        val = self._s._runGuarded(fct2, 4, 7)
        self.assertTrue(val == 4+7)
        self.assertTrue(self._s.alive)

        # Check guarding, create exception
        fct.reset_mock()
        fct.side_effect = ValueError('hello')
        val = self._s._runGuarded(fct, why='this?')
        self.assertTrue(val == None)
        fct.assert_called_once_with(why='this?')
        self.assertFalse(self._s.alive)

        # Check that the function is not called if not alive
        fct.reset_mock()
        fct.side_effect=2
        val = self._s._runGuarded(fct, alive='not')
        self.assertTrue(val == None)
        self.assertFalse(fct.called)
        self.assertFalse(self._s.alive)

        # Resurrect
        self._s.alive = True
        fct2 = lambda e, f: e/f
        val = self._s._runGuarded(fct2, 12, 2)
        self.assertTrue(val == 12 / 2)
        self.assertTrue(self._s.alive)

        # Raise a TypeError
        val = self._s._runGuarded(fct2, 'ez', 'az')
        self.assertFalse(self._s.alive)
        self.assertTrue(val == None)

    @patch('strategy.Strategy.onBars_Guarded')
    @patch('strategy.Strategy.onOrderUpdate_Guarded')
    @patch('strategy.Strategy.stop_Guarded')
    def testStrategyGuardedInterface(self, stop, onOrderUpdate, onBars):
        bar = sentinel.bar
        instrument = sentinel.instrument
        order = sentinel.order

        # Check onBars_Guarded
        onBars.reset_mock()
        onOrderUpdate.reset_mock()
        stop.reset_mock()
        self._s.onBars_Guarded(bar, instrument)
        onBars.assert_called_once_with(bar, instrument)
        self.assertFalse(onOrderUpdate.called)
        self.assertFalse(stop.called)

        # Check onOrderUpdate_Guarded
        onBars.reset_mock()
        onOrderUpdate.reset_mock()
        stop.reset_mock()
        self._s.onOrderUpdate_Guarded(order)
        self.assertFalse(onBars.called)
        onOrderUpdate.assert_called_once_with(order)
        self.assertFalse(stop.called)


