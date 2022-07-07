#!/bin/bash

set -eio pipefail
set -x

session="backtest"
log_file="huba-$(date +%Y%m%d_%H%M).log"

pairlist_dir="201610-sortino-sp500-russell-etfs/"
file_list=$(echo ${pairlist_dir}/*.lst)
tag="sortino-sp500-russell-etfs-201610"
start_date="20070101"
end_date="20131231"

pyenv="../../venv-huba-pypy2-v5.3.1"

# Remove processed pairs from the list
for i in `ls ${pairlist_dir}/*.lst`; do
    python filter-processed-pairs.py ${i} "../logs/backtest-${tag}-*.csv";
done

cmd="${pyenv}/bin/python ../huba.py backtest --from ${start_date} --to ${end_date} --file ${file_list} -t ${tag} -q --multicore | tee ${log_file}"

tmux -2 new-session -d -s $session

tmux split-window -h
tmux select-pane -t 0
tmux send-keys "$cmd" C-m
tmux select-pane -t 1
tmux send-keys "htop" C-m
tmux split-window -v
tmux resize-pane -D 5
tmux send-keys "watch -n 1 -d sensors" C-m

# Set default window
# tmux new-window -t $session:1 -n 'Huba'
# tmux select-window -t $session:1

# Attach to session
# tmux -2 attach-session -t $session
