#!/usr/bin/env python

import logging

from google.protobuf.descriptor_pb2 import DescriptorProto, ServiceDescriptorProto, FieldDescriptorProto

log = logging.getLogger(__name__)

client_header = '''
#
# This file generated from a proto file. You can edit it, but it may 
# get overwritten. This file assumes that you've created standard python 
# grpc stub ans servicer files from the same proto files. It also 
# assumes the existence of the class DistributedAgent declared in 
# a file call distributed_agent.py that is somewhere in the $PYTHON_PATH
#
# Good luck!
#

import logging
import grpc

import {}_pb2 as pb
import {}_pb2_grpc as pb_grpc

from distributed_agent import DistributedAgent, DistributedAgentException
from distributed_agent import DistributedAgentResponses as Responses

log = logging.getLogger(__name__)

'''

servicer_header = '''
#
# This file generated from a proto file. You can edit it, but it may 
# get overwritten. This file assumes that you've created standard python 
# grpc stub ans servicer files from the same proto files.
#

import logging
import grpc

import {}_pb2 as pb
import {}_pb2_grpc as pb_grpc

from distributed_agent import DistributedAgent, DistributedAgentException
from distributed_agent import DistributedAgentResponses as Responses

log = logging.getLogger(__name__)

'''

def field2arg_default(f):
    if f['label'] == FieldDescriptorProto.LABEL_REPEATED:
        return '[]'

    # Types taken from debug out and can be found here:
    # https://github.com/google/protobuf/blob/master/src/google/protobuf/descriptor.proto
    # default is no argument at all. If protobuf 3 syntax supported defaults, we could use
    # them during generation, but it does not.
    type_map = {
        FieldDescriptorProto.TYPE_BOOL: 'False',
        FieldDescriptorProto.TYPE_DOUBLE: 'None',
        FieldDescriptorProto.TYPE_FIXED32: 'None',
        FieldDescriptorProto.TYPE_FIXED64 : 'None',
        FieldDescriptorProto.TYPE_FLOAT: 'None',
        FieldDescriptorProto.TYPE_INT32: 'None',
        FieldDescriptorProto.TYPE_INT64: 'None',
        FieldDescriptorProto.TYPE_SFIXED32: 'None',
        FieldDescriptorProto.TYPE_SFIXED64: 'None',
        FieldDescriptorProto.TYPE_SINT32: 'None',
        FieldDescriptorProto.TYPE_SINT64: 'None',
        FieldDescriptorProto.TYPE_STRING: 'None',
        FieldDescriptorProto.TYPE_UINT32: 'None',
        FieldDescriptorProto.TYPE_UINT64: 'None',
        # Unsupported types - raise exception.
        # FieldDescriptorProto.TYPE_ENUM: 'None',
        # FieldDescriptorProto.TYPE_FIELD_NUMBER: 'None',
        # FieldDescriptorProto.TYPE_MESSAGE: 'None',
        # FieldDescriptorProto.TYPE_NAME_FIELD_NUMBER: 'None',
        # FieldDescriptorProto.TYPE_GROUP: 'None',
        # FieldDescriptorProto.TYPE_BYTES: 'None',
    }

    t = f['type']
    if t not in type_map:
        raise('unsupported type {} in proto file.'.format(t))

    return type_map[t]

def field2defaultarg(f):
    return '{}={}'.format(f['name'], field2arg_default(f))

def generate_client_python(service, methods, name, response):
    f = response.file.add()
    f.name = '{}.py'.format(name)
    log.info('Creating file {}'.format(f.name))
    f.content += client_header.format(name, name)
    f.content += 'class {}Exception(Exception):\n'.format(service)
    f.content += '    pass\n'
    f.content += '\n'
    f.content += 'class {}(DistributedAgent):\n'.format(service)
    f.content += '    def __init__(self, nodes, port=51000):\n'
    f.content += '        super().__init__(nodes, port)\n'
    f.content += '        self.load_agent(\'{}\', pb_grpc.{}Stub)\n'.format(service, service)
    f.content += '\n'
    for method, arg_data in methods.items():
        def_args = [field2defaultarg(field) for field in arg_data['fields']]
        f.content += '    def {}(self, {}):\n'.format(method, ', '.join(def_args))
        f.content += '        return self.blocking_call(\n'
        f.content += '            \'{}\',\n'.format(method)
        f.content += '            pb.{}(\n'.format(arg_data['arg_obj'])
        for field in arg_data['fields']:
            f.content += '                {}={},\n'.format(field['name'], field['name'])
        f.content += '            )\n'
        f.content += '        )\n'
        f.content += '\n'

def generate_servicer_python(service, methods, name, response):
    f = response.file.add()
    f.name = '{}_servicer.py'.format(name)
    log.info('Creating file {}'.format(f.name))

    class_name = '{}Servicer'.format(service)

    f.content = ''
    f.content += servicer_header.format(name, name)

    f.content += 'def AddServicer(server):\n'
    f.content += '    pb_grpc.add_{}_to_server({}(), server)\n'.format(class_name, class_name)
    f.content += '\n'

    f.content += 'class {}Exception(Exception):\n'.format(class_name)
    f.content += '    pass\n'
    f.content += '\n'
    f.content += 'class {}(pb_grpc.{}):\n'.format(class_name, class_name)
    f.content += '    def __init__(self):\n'
    f.content += '        log.debug("{} created.")\n'.format(class_name)
    f.content += '        super().__init__()\n'
    f.content += '\n'
    for method, args in methods.items():
        f.content += '    def {}(self, request, context):\n'.format(method)
        f.content += '        log.debug("Invoking: {}(...)")\n'.format(method)
        for arg in args['fields']:
            f.content += '        {} = request.{}\n'.format(arg['name'], arg['name'])

        f.content += '        # Now use the args above to do the actual work of {}.\n'.format(method)
        f.content += '        # Until then, return a success=False response.\n'
        f.content += '        return pb.Response(success=False, comment="Not implemented.")\n'
        f.content += '\n'

