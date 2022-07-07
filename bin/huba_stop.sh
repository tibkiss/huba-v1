#!/bin/sh

export PATH=/opt/local/bin:/opt/local/sbin:/usr/local/bin:/sbin:/usr/sbin:/Users/tiborkiss/bin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/usr/X11/bin

tmux kill-session -t huba-live

for pid in `ps aux | grep -v "grep" | grep -v "huba_stop.sh" | grep -v "tmux" | grep "huba" | tr -s " " | cut -f 2 -d " "`; do
	kill $pid
done


