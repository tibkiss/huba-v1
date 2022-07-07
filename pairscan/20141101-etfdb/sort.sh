#!/bin/bash

cat backtest-*.csv | sort -t "," -k 7 -n
