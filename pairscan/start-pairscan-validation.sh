#!/bin/bash

set -eio pipefail
set -x

session="backtest-validation"
log_file="huba-$(date +%Y%m%d_%H%M).log"

pairlist_file="201607-iqfeed-1m-sp500-russell-etfs/results/backtest-sp500-russell3000-20160710-top1000.pairs"
tag="sp500-russell3000-20160710-validation"
start_date="20140101"
end_date="20161231"

#pyenv="../venv-huba-pypy-2.6.1"
pyenv="../venv-huba-pypy2-5.3.1"

# Remove processed pairs from the list
python filter-processed-pairs.py ${pairlist_file} "../logs/backtest-${tag}-*.csv";

cmd="${pyenv}/bin/python ../huba.py backtest --from ${start_date} --to ${end_date} --file ${pairlist_file} -t ${tag} -q --multicore | tee ${log_file}"

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
tmux -2 attach-session -t $session
