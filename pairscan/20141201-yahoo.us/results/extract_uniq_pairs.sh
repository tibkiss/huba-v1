#!/bin/sh

filename=$*
echo processing $filename
cat $filename|cut -f 2,3 -d "," | tr \"\[\(\'\)\] \ | sed -e s/" "//g | sed -e s/,/_/ | sort | uniq
