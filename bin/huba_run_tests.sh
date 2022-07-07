#!/bin/bash

# Safety mechanism: 
# -e: Stop the script if any of the command fails in the script.
# -o pipefail: Fail any of the command in a pipeline is failed.
set -eo pipefail

timestamp=`date +%Y%m%d`
logfile="logs/huba-tests-${timestamp}.log"

cd  /Users/tiborkiss/devel/workspace/stocks/huba

source venv-huba-pypy-2.6.1/bin/activate

export PYTHONPATH=../pyalgotrade
(time py.test -s -v testcases) >> ${logfile} 2>&1
