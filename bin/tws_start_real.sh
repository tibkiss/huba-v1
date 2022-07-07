#!/bin/bash


timestamp=`date +%Y%m%d`
log="/Users/tiborkiss/devel/workspace/stocks/huba/logs/tws-real-$timestamp.log"
config="/Users/tiborkiss/devel/workspace/stocks/huba/3rdparty/IBController/IBController-Real.ini"

/Users/tiborkiss/devel/workspace/stocks/huba/3rdparty/IBController/IBControllerStart.sh TWS $config 2>&1 | tee -a $log

