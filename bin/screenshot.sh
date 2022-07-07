#!/bin/sh

currdate=`date +"%Y%m%d"`
currdatetime=`date +"%Y%m%d_%H%M"`
#dirname="/Users/tiborkiss/devel/workspace/stocks/huba/logs/screenshots/${currdate}"
dirname="/Users/tiborkiss/devel/workspace/stocks/huba/logs/screenshots/"
filename="${dirname}/${currdatetime}.png"

mkdir -p ${dirname}

/usr/sbin/screencapture ${filename}
