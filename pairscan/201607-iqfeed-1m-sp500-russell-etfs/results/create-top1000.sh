#!/bin/bash -x

cat backtest-*sorted.csv | sort -k 9 -t "," -n | tail -1000 > backtest-sp500-russell3000-20160710-top1000.csv
