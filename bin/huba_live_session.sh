#!/bin/bash
set -eio pipefail
set -x

HUBA_HOME="/Users/tiborkiss/devel/workspace/stocks/huba"
session="huba-live"

export PATH=/usr/local/bin:/sbin:/usr/sbin:/Users/tiborkiss/bin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/usr/X11/bin

cmd_paper="${HUBA_HOME}/bin/huba_start_paper.sh"
cmd_real="${HUBA_HOME}/bin/huba_start_real.sh"

tmux -2 new-session -d -s ${session}

tmux split-window -v
tmux select-pane -t 0
tmux send-keys "${cmd_paper}" C-m
tmux select-pane -t 1
tmux send-keys "${cmd_real}" C-m

tmux -2 attach-session -t ${session}
