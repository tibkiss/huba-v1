import unittest

import logging
log=logging.getLogger(__name__)


from mock import Mock, MagicMock, patch, sentinel


class Analyzer_Test(unittest.TestCase):
    def setUp(self):
        pass


def getTestCases():
    ret = [Analyzer_Test(e)
           for e in Analyzer_Test.__dict__
           if e.startswith('test')]

    return ret
