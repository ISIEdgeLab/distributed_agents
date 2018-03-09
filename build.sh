#!/usr/bin/env bash

AGENT_PROTO_DIR=agent_proto
PROTO_DIR=./proto 
PYOUT_DIR=./dgrpc
PROTOC3ZIP=./deps/protoc-3.5.1-linux-x86_64.zip
DGRPC_PARSER=./bin/dgrpc_parser.py
# we use protoc3 to support protobuf 3 syntax even though we don't really use it.
PROTOC=/usr/local/bin/protoc3

echo Cleaning the build dir ${PYOUT_DIR}
if [ ! -e ${PYOUT_DIR} ]; then 
    mkdir ${PYOUT_DIR} 
else
    sudo rm -rf ${PYOUT_DIR}/*
fi

#
# use python3 to invoke the protobuf compiler on our proto files to generate python files. 
#
# generate the pb2, anfd grpc python files. 
echo Generating protobuf and grpc python code.
python3 -m grpc_tools.protoc \
    -I${PROTO_DIR} \
    -I${AGENT_PROTO_DIR} \
    --python_out=${PYOUT_DIR} \
    --grpc_python_out=${PYOUT_DIR} \
    ${PROTO_DIR}/*.proto \
    ${AGENT_PROTO_DIR}/*.proto

# generate the dgrpc client-side files. 
# (This auto install of the protoc3 compiler should be elsewhere.)
if [ ! -e ${PROTOC} ]; then
    pushd /tmp
    unzip ${PROTOC3ZIP} -d protoc
    sudo cp -v protoc/bin/protoc ${PROTOC}
    sudo cp -v -r protoc/include/* /usr/local/bin/include
    popd

    sudo apt install -y protobuf-compiler
    sudo apt install -y python-protobuf
fi

echo Generating distributed agent client-side code.
# Invoke our parser to generate "dgrpc" files.
${PROTOC} -I ${AGENT_PROTO_DIR} \
    --plugin=protoc-gen-dgrpc=${DGRPC_PARSER} \
    --dgrpc_out=${PYOUT_DIR} \
    ${AGENT_PROTO_DIR}/*.proto

echo Overwriting servicer templates with working servicers from src...
cp -v src/*_servicer.py ${PYOUT_DIR}

# hack for extra files for apache. This will be cleaned up somehow.
cp -v src/traffic_gen* ${PYOUT_DIR}


# This file is not generated, but maybe should be. It's the base class for the distribute (client-side) agents.
cp ./bin/distributed_agent.py ${PYOUT_DIR}

echo Done.
