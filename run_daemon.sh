#!/usr/bin/env bash

if [[ $(id -u) -ne 0 ]]; then 
    echo Please run under sudo or as root.
    exit 1
fi

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [[ $1 == stop ]]; then 
    pkill -f agent_server.py
    exit 0
fi

PYTHONPATH=${DIR}/dgrpc:${DIR}/dgrpc/pb ${DIR}/bin/agent_server.py -v > /tmp/dgrpc.log 2>&1 &

exit 0
