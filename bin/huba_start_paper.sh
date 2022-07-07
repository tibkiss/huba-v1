#!/bin/bash
set -eio pipefail
set -x

export HUBA_HOME="/Users/tiborkiss/devel/workspace/stocks/huba"

pyenv="${HUBA_HOME}/venv-huba-pypy-2.6.1"

timestamp=`date +%Y%m%d`
error_log="logs/huba-paper-${timestamp}.err"

cd ${HUBA_HOME}
${pyenv}/bin/python huba.py live-trade --paper --debug --console 2> >(tee -a ${error_log})
