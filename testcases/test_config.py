__author__ = 'tiborkiss'

import unittest
from config import StatArbConfig, StatArbPairsParams
from strategy.statarb_params import StatArbParams

class ConfigTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def testStatArbConfig(self):
        self.assertTrue('Real' in StatArbConfig)
        self.assertTrue('Paper' in StatArbConfig)
        self.assertTrue('Test' in StatArbConfig)
        self.assertTrue(len(StatArbConfig.keys()) == 3)

        # Real
        self.assertTrue(StatArbConfig['Real']['AccountCode'].startswith('U'))
        self.assertTrue(StatArbConfig['Real']['TWSConnection'] == 'tws-real:7500:53')

        # Paper
        self.assertTrue(StatArbConfig['Paper']['AccountCode'].startswith('DU'))
        self.assertTrue(StatArbConfig['Paper']['TWSConnection'] == 'tws-paper:7500:53')

        # Test
        self.assertTrue(StatArbConfig['Test']['AccountCode'].startswith('DU'))
        self.assertTrue(len(StatArbConfig['Test']['Pairs']) == 0)

        # Real + Paper
        for action in ('Real', 'Paper'):
            self.assertTrue(0.3 <= StatArbConfig[action]['Leverage'] <= 2.0)
            self.assertTrue(isinstance(StatArbConfig[action]['Leverage'], float))
            self.assertTrue(len(StatArbConfig[action]['Pairs']) >= 5)
            symbols = set()
            for pair in StatArbConfig[action]['Pairs']:
                p = pair.split('_')
                self.assertTrue(len(p) == 2)
                assert(tuple(p) in StatArbPairsParams[action])

                # Check for duplicate symbols through all the pairs
                for i in (0, 1):
                    self.assertFalse(p[i] in symbols, "%s from %s is used by other pair" % (p[i], pair))
                    symbols.add(p[i])


    def testStatArbPairsParams(self):
        for action in ('Real', 'Paper', 'Test'):
            for cfg in StatArbPairsParams[action]:
                self.assertTrue(len(cfg) == 2)
                self.assertTrue(isinstance(StatArbPairsParams[action][cfg], StatArbParams))
