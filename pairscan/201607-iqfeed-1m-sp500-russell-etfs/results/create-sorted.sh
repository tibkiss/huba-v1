#!/bin/sh -x

cat backtest-sp500-20160710-PoolWorker-*  | sort -k 9 -t "," -n  | uniq -s 27 > backtest-sp500-2060710-sorted.csv
cat backtest-russell-3000-20160710-PoolWorker-*  | sort -k 9 -t "," -n  | uniq -s 27 > backtest-russell-3000-2060710-sorted.csv
