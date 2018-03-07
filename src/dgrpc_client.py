#!/usr/bin/env python

import logging
from sys import stderr as STDERR, stdin as STDIN, stdout as STDOUT

from google.protobuf.compiler import plugin_pb2 as plugin
from google.protobuf.descriptor_pb2 import DescriptorProto, ServiceDescriptorProto, FieldDescriptorProto

log = logging.getLogger(__name__)

# We write log data to stderr as this script uses stdin and stdout for work.
log_level = logging.INFO
err_h = logging.StreamHandler(STDERR)
err_h.setLevel(log_level)
log.addHandler(err_h)
log.setLevel(log_level)

header = '''
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

def _debug(msg):
    '''We do a lot of debug statements as we cannot use pdb to examing the datatypes that 
        the google protobuf library is giving to us. So we just print them out. Annoying,
        but useful.
    '''
    log.debug(msg)
    log.debug('-'*80)

def field2arg_default(f):
    if f['label'] == FieldDescriptorProto.LABEL_REPEATED:
        return '[]'

    # Types taken from debug out and can be found here:
    # https://github.com/google/protobuf/blob/master/src/google/protobuf/descriptor.proto
    type_map = {
        FieldDescriptorProto.TYPE_BOOL: 'False',
        FieldDescriptorProto.TYPE_DOUBLE: '0.0',
        FieldDescriptorProto.TYPE_FIXED32: '0',
        FieldDescriptorProto.TYPE_FIXED64 : '0',
        FieldDescriptorProto.TYPE_FLOAT: '0.0',
        FieldDescriptorProto.TYPE_INT32: '0',
        FieldDescriptorProto.TYPE_INT64: '0',
        FieldDescriptorProto.TYPE_SFIXED32: '0',
        FieldDescriptorProto.TYPE_SFIXED64: '0',
        FieldDescriptorProto.TYPE_SINT32: '0',
        FieldDescriptorProto.TYPE_SINT64: '0',
        FieldDescriptorProto.TYPE_STRING: '""',
        FieldDescriptorProto.TYPE_UINT32: '0',
        FieldDescriptorProto.TYPE_UINT64: '0',
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

def field2arg(f):
    return '{}={}'.format(f['name'], field2arg_default(f))

if __name__ == '__main__':
    # Read request message from stdin
    request_data = STDIN.read()

    # Parse request
    request = plugin.CodeGeneratorRequest()
    request.ParseFromString(request_data)

    # loop over the proto data and build up a dict which has the information we need.
    #_debug('reading request')
    for proto_file in request.proto_file:
        log.info('Parsing proto file {}'.format(proto_file))
        data = {'services': {}, 'messages': {}}
        #_debug('reading file: \n{}'.format(proto_file))
        data['package'] = proto_file.package

        # First read in all the "messages". These are the arugments to the methods in our service.
        for message in proto_file.message_type:
            #_debug('message: \n{}'.format(message))
            #_debug('message type: {}'.format(type(message)))
            data['messages'][message.name] = {}
            fields = []
            for f in message.field:
                # _debug('f dir: {}'.format(dir(f))); exit(0)
                fields.append({
                    'name': f.name,
                    'type': f.type,
                    'number': f.number,
                    'label': f.label
                })
                # Do we need to sort by number here?

            data['messages'][message.name]['fields'] = fields
       
        # Now read all the methods in our services, and build a method signature.
        for service in proto_file.service:
            _debug('serv type: {}'.format(type(service)))
            _debug('serv dir: {}'.format(dir(service)))
            _debug('service: \n{}'.format(service))
            data['services'][service.name] = {}

            # example method data:
            # method {                                       
            #   name: "Configure"                            
            #   input_type: ".http_client_agent.ConfigArgs"  
            #   output_type: ".http_client_agent.Response"   
            #   options {                                    
            #   }                                            
            # }                                              
            for method in service.method:
                _debug('method: \n{}'.format(method))
                data['services'][service.name][method.name] = {}
                _, packname, messname = method.input_type.split('.')
                _debug('looking for {} in {}'.format(messname, data['messages']))
                if packname == data['package']:  # I think this is always true?
                    if messname in data['messages']:  # We have a corresponding "message" that describes the args.
                        data['services'][service.name][method.name]['fields'] = data['messages'][messname]['fields']

                data['services'][service.name][method.name]['arg_obj'] = messname

            #_debug('found service: \n{}'.format(service))

        _debug('data: \n{}'.format(data))

        # Create response and fill it with python.
        response = plugin.CodeGeneratorResponse()

        for service, methods in data['services'].items():
            f = response.file.add()
            f.name = '{}.py'.format(data['package'])
            log.info('Creating file {}'.format(f.name))
            f.content = ''
            f.content += header.format(data['package'], data['package'])
            f.content += 'class {}(DistributedAgent):\n'.format(service)
            f.content += '    def __init__(self, nodes, port=51000):\n'
            f.content += '        super().__init__(nodes, port)\n'
            f.content += '        self.load_agent(\'{}\', pb_gprc.{}Stub)\n'.format(service, service)
            f.content += '\n'
            for method, arg_data in methods.items():
                args = [field2arg(field) for field in arg_data['fields']]
                f.content += '    def {}({}):\n'.format(method, ', '.join(args))
                f.content += '        return self.blocking_call(\n'
                f.content += '            \'{}\',\n'.format(method)
                f.content += '            pb.{}(\n'.format(arg_data['arg_obj'])
                for arg in args:
                    f.content += '                {},\n'.format(arg)
                f.content += '            )\n'
                f.content += '        )\n'
                f.content += '\n'

        # Serialise response message
        output = response.SerializeToString()

        # Write to stdout. The protocol compiler will generate the files. 
        STDOUT.write(output)

    exit(0)
