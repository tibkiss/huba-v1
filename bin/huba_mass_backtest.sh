#!/bin/bash

if [ $# != 1 ]; then
    echo "Usage: ./huba_mass_backtest.sh filename"
    exit
fi

filename=$1
if [ ! -f $filename ]; then
    echo "Input file does not exists: $filename"
    exit
fi

HUBADIR=/home/tibkiss/devel/workspace/stocks/huba
for i in `cat $filename`; do
    tag=`basename $filename`
    ${HUBADIR}/huba.py --action backtest --bt-start-date 20090101 --bt-end-date 20131231 --tag $tag --pairs $i
done
