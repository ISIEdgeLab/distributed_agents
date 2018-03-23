#!/usr/bin/env bash

PROTO_DIR=proto 
PACKAGE_DIR=dgrpc
PROTOC3ZIP=./sources/protoc-3.5.1-linux-x86_64.zip
DGRPC_PARSER=./bin/dgrpc_parser.py
# we use protoc3 to support protobuf 3 syntax even though we don't really use it.
PROTOC=/usr/local/bin/protoc3

echo Cleaning the build dir ${PACKAGE_DIR}
rm -rf ${PACKAGE_DIR} &> /dev/null 
mkdir -p ${PACKAGE_DIR} &> /dev/null

#
# use python3 to invoke the protobuf compiler on our proto files to generate python files. 
#
# generate the pb2, anfd grpc python files. 
echo Generating protobuf and grpc python code.
# The dir tree under proto must match the output dir or the imports in the generated code are not 
# relative. THis is stupid and a bug (I'm hoping) in the python generation code. 
python3 -m grpc_tools.protoc \
    -I${PROTO_DIR} \
    --python_out=. \
    --grpc_python_out=. \
    ${PROTO_DIR}/${PACKAGE_DIR}/*.proto 

if [[ $? -ne 0 ]]; then
    echo Error building python agents from proto files, aborting.
    echo See build errors above. 
    exit 1
fi

# generate the dgrpc client-side files. 
# (This auto install of the protoc3 compiler should be elsewhere.)
if [ ! -e ${PROTOC} ]; then
    echo protoc3 not found, installing locally on $(hostname -s)
    unzip ${PROTOC3ZIP} -d /tmp/protoc
    sudo cp -v /tmp/protoc/bin/protoc ${PROTOC}
    sudo cp -v -r /tmp/protoc/include/* /usr/local/bin/include
    sudo apt install -y protobuf-compiler
    sudo apt install -y python-protobuf
fi

echo Generating distributed agent client and server side code.
# Invoke our parser to generate "dgrpc" files.
${PROTOC} \
    -I ${PROTO_DIR} \
    --plugin=protoc-gen-dgrpc=${DGRPC_PARSER} \
    --dgrpc_out=${PACKAGE_DIR} \
    ${PROTO_DIR}/${PACKAGE_DIR}/*.proto

echo Overwriting servicer templates with working servicers from staging...
cp -v staging/*_servicer.py ${PACKAGE_DIR}

# hack for extra files for apache. This will be cleaned up somehow.
cp -v staging/traffic_gen* ${PACKAGE_DIR}

# This file is not generated, but maybe should be. It's the base class for the distribute (client-side) agents.
cp ./bin/distributed_agent.py ${PACKAGE_DIR}

touch ${PACKAGE_DIR}/__init__.py    # make this into a python package. 
echo Done.
