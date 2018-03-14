#!/usr/bin/env python3

import logging
import sys

from google.protobuf.compiler import plugin_pb2 as plugin
from google.protobuf.descriptor_pb2 import DescriptorProto, ServiceDescriptorProto, FieldDescriptorProto

from dgrpc_generator import generate_client_python, generate_servicer_python

log = logging.getLogger(__name__)

if __name__ == '__main__':
    # Read request message from stdin (as binary)
    request_data = sys.stdin.buffer.read()

    # Parse request
    request = plugin.CodeGeneratorRequest()
    request.ParseFromString(request_data)

    # Create response and fill it with python.
    response = plugin.CodeGeneratorResponse()

    # generate client and service-stub files in python.
    for proto_file in request.proto_file:
        log.info('Parsing proto file {}'.format(proto_file.name))
        generate_client_python(proto_file, response)
        generate_servicer_python(proto_file, response)
        
    # Serialize response message
    output = response.SerializeToString()

    # Write to stdout. The protocol compiler will generate the files. 
    sys.stdout.buffer.write(output)

    exit(0)
