#!/bin/bash

export PYTHONPATH=/Users/tiborkiss/devel/workspace/stocks/huba

cd  /Users/tiborkiss/devel/workspace/stocks/huba 
source venv-huba-pypy-2.6.1/bin/activate
./tools/google_intraday.py $*
