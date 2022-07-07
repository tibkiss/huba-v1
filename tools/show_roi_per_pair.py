import sys
import pandas as pd

def show_roi_per_pair(filename):
    r = pd.read_csv(filename)
    gb = r.groupby('Pair')
    gbs = gb.ROI.sum()
    gbs.sort()

    print gbs

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print 'Usage: '
        print '%s filename' % sys.argv[0]
        sys.exit(1)

    show_roi_per_pair(sys.argv[1])
