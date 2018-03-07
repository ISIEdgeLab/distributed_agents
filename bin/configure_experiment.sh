#!/usr/bin/env bash

# assumes doAll is in $PATH somewhere

# install grpc and grpc python tools
doAll -p sudo apt-get install -y python3-pip
doAll -p sudo pip3 install --no-index -f /users/glawler/tmp/grpcio-tools-pip grpcio-tools

# needed for agent_server.py
doAll -p sudo apt-get install python3-netifaces
