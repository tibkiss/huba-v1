from __future__ import print_function
from collections import namedtuple

import unittest
import sys

from huba import main

from config import StatArbConfig

_MinMaxTuple = namedtuple('MinMaxTuple', ['min', 'max'])
PERFORMANCE_REQUIREMENTS = { 'dayCount' : _MinMaxTuple(215, 1500),
                             'finalPortfolio' : _MinMaxTuple(0, float('Inf')),
                             'cumReturn' : _MinMaxTuple(5, 700),
                             'CAGR': _MinMaxTuple(5, 100),
                             'sharpe': _MinMaxTuple(0.1, 5),
                             'maxDrawDown': _MinMaxTuple(0, 40),
#                             'drawDownDaysPct': _MinMaxTuple(0, 75)  # Percent of the day count
                           }

PERFORMANCE_EXEMPTIONS = { 'BTI_PM':    { 'sharpe':    _MinMaxTuple(-0.19, PERFORMANCE_REQUIREMENTS['sharpe'].max), 
                                          'cumReturn': _MinMaxTuple(3.39, PERFORMANCE_REQUIREMENTS['cumReturn'].max),
                                          'CAGR':      _MinMaxTuple(3.39, PERFORMANCE_REQUIREMENTS['CAGR'].max) 
                                        },
                           'ACC_BIP':   { 'sharpe' :   _MinMaxTuple(0.04, PERFORMANCE_REQUIREMENTS['sharpe'].max), },
                           'PMCS_SPIL': { 'sharpe':    _MinMaxTuple(-0.03, PERFORMANCE_REQUIREMENTS['sharpe'].max),
                                          'CAGR':      _MinMaxTuple(2.61, PERFORMANCE_REQUIREMENTS['CAGR'].max),
                                          'cumReturn': _MinMaxTuple(2.6, PERFORMANCE_REQUIREMENTS['cumReturn'].max) 
                                        },
                           'LH_STE': { 'sharpe':       _MinMaxTuple(0, PERFORMANCE_REQUIREMENTS['sharpe'].max),
                                       'cumReturn':    _MinMaxTuple(4.7, PERFORMANCE_REQUIREMENTS['cumReturn'].max),
                                       'CAGR':         _MinMaxTuple(4.7, PERFORMANCE_REQUIREMENTS['CAGR'].max),
                                     },
                           'CXO_TCP': { 'sharpe':     _MinMaxTuple(-1.02, PERFORMANCE_REQUIREMENTS['sharpe'].max),
                                        'CAGR':       _MinMaxTuple(-25.52, PERFORMANCE_REQUIREMENTS['CAGR'].max),
                                        'cumReturn':  _MinMaxTuple(-25.43, PERFORMANCE_REQUIREMENTS['cumReturn'].max),
                                        'maxDrawDown':_MinMaxTuple(PERFORMANCE_REQUIREMENTS['maxDrawDown'].min, 50),
                                     },
                           'INSY_NBIX': {'maxDrawDown':_MinMaxTuple(PERFORMANCE_REQUIREMENTS['maxDrawDown'].min, 50)},
                           'MTW_TEX':   {'CAGR':       _MinMaxTuple(4.6, PERFORMANCE_REQUIREMENTS['CAGR'].max)},
                           'CRH_MLM':   {'CAGR':       _MinMaxTuple(2, PERFORMANCE_REQUIREMENTS['CAGR'].max),
                                         'sharpe':     _MinMaxTuple(-0.12, PERFORMANCE_REQUIREMENTS['sharpe'].max)}
                         }

class Huba_SystemTest(unittest.TestCase):
    def _verifyRanges(self, instrument, stats):
        failed = False
        failFields = []

        for key in PERFORMANCE_REQUIREMENTS:
            if instrument in PERFORMANCE_EXEMPTIONS and key in PERFORMANCE_EXEMPTIONS[instrument]:
                min_value = PERFORMANCE_EXEMPTIONS[instrument][key].min
                max_value = PERFORMANCE_EXEMPTIONS[instrument][key].max 
            else:
                min_value = PERFORMANCE_REQUIREMENTS[key].min
                max_value = PERFORMANCE_REQUIREMENTS[key].max

            if not (min_value <= stats[key] <= max_value):
                failed = True
                failFields.append(key)

        if not (0 <= stats['drawDownDays'] <= stats['dayCount'] * 0.80):  # 80% of the period
            failed = True
            failFields.append("drawDownDaysPct")

        failFieldsStr = ", ".join(failFields)

        stateStr = "FAIL (%s)" % failFieldsStr if failed else "SUCCESS"
        print("%s: %s dayCount=%d sharpe=%.2f CAGR=%.2f%% cumReturn=%.2f%% finalPortfolio=%d maxDrawDown=%.2f drawDownDays=%d" %
              (stateStr, instrument,
               stats['dayCount'], stats['sharpe'], stats['CAGR'], stats['cumReturn'], stats['finalPortfolio'], stats['maxDrawDown'], stats['drawDownDays']),
              file=sys.stderr)

        return failed

    def testBacktest_OneByOne(self):
        print('Running backtests:', file=sys.stderr)
        failed = {}
        for instrument in StatArbConfig['Real']['Pairs']:
            args = 'backtest --from 20140101 --to 20161231 --instr %s --freq 1M -q --tag=SystemTest' % instrument
            print ('./huba.py %s' % args, file=sys.stderr)
            stats = main(args.split())
            failed[instrument] = self._verifyRanges(instrument, stats[0])
            print ('', file=sys.stderr)

        for k in failed:
            self.assertFalse(failed[k])

        print('All ok', file=sys.stderr)
