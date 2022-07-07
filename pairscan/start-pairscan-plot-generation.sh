#!/bin/bash

set -eio pipefail
set -x

session="backtest-validation-plots"
log_file="huba-$(date +%Y%m%d_%H%M).log"

pairlist_file="201607-iqfeed-1m-sp500-russell-etfs/results/backtest-sp500-russell3000-20160710-validation-top100.pairs"
tag="sp500-russell3000-20160710-validation"
start_date1="20070101"
start_date2="20140101"
end_date="20161231"

pyenv="../venv-huba-python-2.7.5"

# Remove processed pairs from the list
cmd1="${pyenv}/bin/python ../huba.py backtest --from ${start_date1} --to ${end_date} --file ${pairlist_file} -t ${tag} -q --multicore --saveplot"
cmd2="${pyenv}/bin/python ../huba.py backtest --from ${start_date2} --to ${end_date} --file ${pairlist_file} -t ${tag} -q --multicore --saveplot"

tmux -2 new-session -d -s $session

tmux split-window -h
tmux select-pane -t 0
tmux send-keys "$cmd1" C-m
tmux send-keys "$cmd2" C-m

# Set default window
# tmux new-window -t $session:1 -n 'Huba'
# tmux select-window -t $session:1

# Attach to session
tmux -2 attach-session -t $session
