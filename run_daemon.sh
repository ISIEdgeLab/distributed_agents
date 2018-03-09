#!/usr/bin/env bash

if [[ $(id -u) -ne 0 ]]; then 
    echo Please run under sudo or as root.
    exit 1
fi

PYTHONPATH=$(pwd)/dgrpc ./bin/agent_server.py -v
