#!/usr/bin/env python3

import logging
import sys
import re   # now I've got two problems.

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

import sys
sys.path.append('./pb')  # GTL: Ugh. Find a better way to do this.

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
import sys

import sys
sys.path.append('./pb')  # GTL: Ugh. Find a better way to do this.

import {}_pb2 as pb
import {}_pb2_grpc as pb_grpc

log = logging.getLogger(__name__)

'''

def field2arg_default(f):
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
        FieldDescriptorProto.TYPE_STRING: "''",
        FieldDescriptorProto.TYPE_UINT32: 'None',
        FieldDescriptorProto.TYPE_UINT64: 'None',
        FieldDescriptorProto.TYPE_MESSAGE: 'None',
        # Unsupported types - raise exception.
        # FieldDescriptorProto.TYPE_ENUM: 'None',
        # FieldDescriptorProto.TYPE_FIELD_NUMBER: 'None',
        # FieldDescriptorProto.TYPE_NAME_FIELD_NUMBER: 'None',
        # FieldDescriptorProto.TYPE_GROUP: 'None',
        # FieldDescriptorProto.TYPE_BYTES: 'None',
    }

    t = f.type
    if t not in type_map:
        raise('unsupported type {} in proto file.'.format(t))

    return type_map[t]

# The problem is nested messages. I need to get the ArgumentMessage name for all nested messages. 
# The call to blocking_call() with a nested message will look like:
# blocking_call(
#           pb.OutsideArgs(
#               one=1,
#               two=2,
#               pb.InsideArgs(
#                   three=3,
#                   four=4
#               )
#           )
# )
# This is not needed for python dicts, which is why I wrote it. For dicts, we can just 
# use the map<> protobuf type.
def message2invocation(message, defaults=False):
    '''take a message and convert it into something that looks like a function call:
        Foobar(one=one, two=two, three=BarBar(four=four, five=five))
    If defaults is True, use the default of the types rather than the actual variables:
        Foobar(one=None, two='', three=BarBar(four=None, five=None))
    '''
    args = []
    for f in message.field:
        if f.type == FieldDescriptorProto.TYPE_MESSAGE:
            # foo=SomeMessage(...). Need a recursive call to resolve the arguments. 
            _, _, _, nested_message_name = f.type_name.split('.', maxsplit=3)
            sys.stderr.write('looking for nested: {}\n'.format(nested_message_name))
            for nested_message in message.nested_type:
                sys.stderr.write('Looking at {}\n'.format(nested_message.name))
                if nested_message.name == nested_message_name:
                    args.append(message2invocation(nested_message))
        else:
            if not defaults:
                # foo=foo
                args.append('{}={}'.format(f.name, f.name))
            else:
                # foo=False or foo=None
                args.append('{}={}'.format(f.name, field2arg_default(f)))

    return '{}({})'.format(message.name, ', '.join(args))

def _service_to_filename(service):
    '''Given a service message, generate a string that can be used as a filename (without extension).'''
    def repl(match):
        return '_{}'.format(match.group(0).lower())
    
    return re.sub('[A-Z]', repl, service.name).lstrip('_')

# see https://github.com/google/protobuf/blob/master/src/google/protobuf/descriptor.proto 
# which decribes everything in the proto_file instance. It's apython protobuf instance.
def generate_client_python(proto_file, response):
    '''take a proto_file instance and build a python client-side wrapper(s) for the proto. Assumes existence
    of teh pb2 and p2_grpc files and classes for the agent(s).'''
    for service in proto_file.service:
        # service is a ServiceDescriptorProto instance. 
        # create a file to write to. 
        f = response.file.add()
        f.name = '{}.py'.format(_service_to_filename(service))
        log.info('Creating file {}'.format(f.name))

        # "header" is everything before class def and is given in client_header above.
        f.content += client_header.format(proto_file.package, proto_file.package)
        
        # make a class specific exception. 
        f.content += 'class {}Exception(Exception):\n'.format(service.name)
        f.content += '    pass\n'
        f.content += '\n'

        # __init__ simply calls the DistributedAgent base, whcih does most of the work.
        f.content += 'class {}(DistributedAgent):\n'.format(service.name)
        f.content += '    def __init__(self, nodes, port=51000):\n'
        f.content += '        super().__init__(nodes, port)\n'
        f.content += '        self.load_agent(\'{}\', pb_grpc.{}Stub)\n'.format(service.name, service.name)
        f.content += '\n'

        # now generate methods calls. They pass off the args to a base class method that does the real work.
        for method in service.method:                   # method is a MethodDescriptorProto instance. 
            # we have two sets of args to get, one for the kwargs of teh method defination and one for
            # the actual calling into the base class method.
            # def foobar(self, one=None, two=0):
            #     return self.blocking_call(ArgMessage(one=one, two=two)
            #
            _, _, in_message_name = method.input_type.split(sep='.', maxsplit=2)
            in_message = [m for m in proto_file.message_type if m.name == in_message_name][0]
            _, _, out_message_name = method.output_type.split(sep='.', maxsplit=2)
            out_message = [m for m in proto_file.message_type if m.name == out_message_name][0]

            def_args = ['{}={}'.format(f.name, field2arg_default(f)) for f in in_message.field]
            invoke_args = ['{}={}'.format(f.name, f.name) for f in in_message.field]

            f.content += '    # returns --> pb.{}\n'.format(message2invocation(out_message))
            f.content += '    def {}({}):\n'.format(method.name, ', '.join(['self'] + def_args))
            f.content += '       return self.blocking_call(\n'
            f.content += '           \'{}\',\n'.format(method.name)
            f.content += '           pb.{}({})\n'.format(in_message_name, ', '.join(invoke_args))
            f.content += '       )\n'
            f.content += '    \n'

def generate_servicer_python(proto_file, response):
    for service in proto_file.service:
        f = response.file.add()
        filename = _service_to_filename(service)
        f.name = '{}_servicer.py'.format(filename)
        log.info('Creating file {}'.format(f.name))

        class_name = '{}Servicer'.format(service.name)

        f.content = ''
        f.content += servicer_header.format(proto_file.package, proto_file.package)

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
        for method in service.method:
            _, _, in_message_name = method.input_type.split(sep='.', maxsplit=2)
            in_message = [m for m in proto_file.message_type if m.name == in_message_name][0]
            _, _, out_message_name = method.output_type.split(sep='.', maxsplit=2)
            out_message = [m for m in proto_file.message_type if m.name == out_message_name][0]

            f.content += '    # returns pb.{}\n'.format(message2invocation(out_message))
            f.content += '    def {}(self, request, context):\n'.format(method.name)
            f.content += '        log.debug("Invoking: {}(...)")\n'.format(method.name)
            for field in in_message.field:
                f.content += '        {} = request.{}\n'.format(field.name, field.name)

            if len(in_message.field):
                f.content += '        # Now use the args above to do the actual work of {}.\n'.format(method.name)
                f.content += '        # Until then, return a success=False response.\n'

            f.content += '        return pb.{}\n'.format(message2invocation(out_message, defaults=True))
            f.content += '\n'

