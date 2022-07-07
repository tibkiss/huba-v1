"""Filter finished backtests from batch.

 Usage:
   ./filter_finished_backtest_from_batch.py <batchFile> <backtestCSVGlob>...
"""
__author__ = 'tiborkiss'
import sys
import csv
from datetime import datetime
from glob import glob

from tools.docopt import docopt


def main(argv):
    args = docopt(__doc__, argv=argv, version=1.0)

    batchFile = []
    print 'Reading batch file'
    with open(args['<batchFile>'], 'r') as batch:
        for line in batch:
            batchFile.append(line.rstrip())

    #print batchFile
    for filename in args['<backtestCSVGlob>']:
        print 'Reading backtest result csv: %s' % filename
        with open(filename, 'r') as btFile:
            #reader = csv.DictReader(btFile, fieldnames=['BTDate','Version','Pairs','StartDate','EndDate','BarFreq',
            #                                            'BarCount','DayCount','Sharpe','CAGR','CumRet','MaxDD','DDDur',
            #                                            'lookbackWindow','EntryZScore','ExitZScore','ZScoreEvalFreq',],
            #                                            delimiter=',')
            reader = csv.DictReader(btFile)
            for row in reader:
                if row['Pairs'] in batchFile:
                    #print 'Marking %s completed' % row['Pairs']
                    batchFile.remove(row['Pairs'])


    dtStr = datetime.now().strftime("%y%m%d_%H%M%S")
    resultFilename = '%s-resume-%s' % (args['<batchFile>'], dtStr)
    print 'Creating %s' % resultFilename
    with open(resultFilename, 'w') as result:
        for pair in batchFile:
            result.write('%s\n' % pair)

    print 'done'


if __name__ == '__main__':
    main(sys.argv[1:])