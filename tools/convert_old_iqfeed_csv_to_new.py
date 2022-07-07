__author__ = 'tiborkiss'

# - Add CSV Header
# - replace ; by ,
# - get rid of .0 in the last column (Volume)


import glob
import os
import sys

files = glob.glob('.csvCache/*-iqfeed.csv')

print "Found %d files" % len(files)

for i, file in enumerate(files):
    print 'processing %s (%d out of %d)' % (file, i, len(files))

    if os.path.exists('%s.old' % file):
        print 'Already processed, skipping'
        continue

    with open(file, "r") as input:
        with open("%s.new" % file, "w") as output:
            # Read the lines
            lines = input.readlines()

            if not lines[0].startswith('Date'):
                # header is missing
                output.write("Date Time,Open,High,Low,Close,Volume\r\n")

            for line in lines:
                newLine = line.replace(';', ',')  # replace ; by ,
                if newLine.endswith('.0\r\n'):
                    newLine = "%s\r\n" % newLine[0:-4]  # strip out .0 from volume
                output.write(newLine)

    os.rename(file, "%s.old" % file)
    os.rename("%s.new" % file, file)
    os.remove("%s.old" % file)
