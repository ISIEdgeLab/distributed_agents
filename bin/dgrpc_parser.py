#!/usr/bin/env python

import logging
from sys import stderr as STDERR, stdin as STDIN, stdout as STDOUT

from google.protobuf.compiler import plugin_pb2 as plugin
from google.protobuf.descriptor_pb2 import DescriptorProto, ServiceDescriptorProto, FieldDescriptorProto

from dgrpc_generator import generate_client_python, generate_servicer_python

log = logging.getLogger(__name__)

# We write log data to stderr as this script uses stdin and stdout for work.
log_level = logging.INFO
err_h = logging.StreamHandler(STDERR)
err_h.setLevel(log_level)
log.addHandler(err_h)
log.setLevel(log_level)

def _debug(msg):
    '''We do a lot of debug statements as we cannot use pdb to examing the datatypes that 
        the google protobuf library is giving to us. So we just print them out. Annoying,
        but useful.
    '''
    log.debug(msg)
    log.debug('-'*80)

if __name__ == '__main__':
    # Read request message from stdin
    request_data = STDIN.read()

    # Parse request
    request = plugin.CodeGeneratorRequest()
    request.ParseFromString(request_data)

    # loop over the proto data and build up a dict which has the information we need.
    #_debug('reading request')
    for proto_file in request.proto_file:
        log.info('Parsing proto file {}'.format(proto_file.name))
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
            # _debug('serv type: {}'.format(type(service)))
            # _debug('serv dir: {}'.format(dir(service)))
            # _debug('service: \n{}'.format(service))
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
                # _debug('method: \n{}'.format(method))
                data['services'][service.name][method.name] = {}
                _, packname, messname = method.input_type.split('.')
                # _debug('looking for {} in {}'.format(messname, data['messages']))
                if packname == data['package']:  # I think this is always true?
                    if messname in data['messages']:  # We have a corresponding "message" that describes the args.
                        data['services'][service.name][method.name]['fields'] = data['messages'][messname]['fields']

                data['services'][service.name][method.name]['arg_obj'] = messname

            #_debug('found service: \n{}'.format(service))

        # _debug('data: \n{}'.format(data))

        # Create response and fill it with python.
        response = plugin.CodeGeneratorResponse()

        for service, methods in data['services'].items():
            generate_client_python(service, methods, data['package'], response)
            generate_servicer_python(service, methods, data['package'], response)
        
        # Serialize response message
        output = response.SerializeToString()

        # Write to stdout. The protocol compiler will generate the files. 
        STDOUT.write(output)

    exit(0)
