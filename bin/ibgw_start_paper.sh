#!/bin/bash


timestamp=`date +%Y%m%d`
log="/Users/tiborkiss/devel/workspace/stocks/huba/logs/ibgw-paper-$timestamp.log"
config="/Users/tiborkiss/devel/workspace/stocks/huba/3rdparty/IBController/IBController-Paper.ini"

/Users/tiborkiss/devel/workspace/stocks/huba/3rdparty/IBController/IBControllerStart.sh GW $config 2>&1 | tee -a $log

