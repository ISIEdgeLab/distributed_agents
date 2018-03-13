#!/usr/bin/env python

import logging
import itertools
import json
import sys

from google.protobuf.compiler import plugin_pb2 as plugin
from google.protobuf.descriptor_pb2 import DescriptorProto, ServiceDescriptorProto, FieldDescriptorProto, EnumDescriptorProto

log = logging.getLogger(__name__)

def traverse(proto_file):
    def _traverse(package, items):
        for item in items:
            yield item, package

            if isinstance(item, DescriptorProto):
                for enum in item.enum_type:
                    yield enum, package

                for nested in item.nested_type:
                    nested_package = package + item.name

                    for nested_item in _traverse(nested, nested_package):
                        yield nested_item, nested_package

    return itertools.chain(
        _traverse(proto_file.package, proto_file.enum_type),
        _traverse(proto_file.package, proto_file.message_type),
        _traverse(proto_file.package, proto_file.service),
    )

if __name__ == '__main__':
    # Read request message from stdin
    request_data = sys.stdin.read()

    # Parse request
    request = plugin.CodeGeneratorRequest()
    request.ParseFromString(request_data)

    # _debug('request: \n{}'.format(dir(request)))
    for proto_file in request.proto_file:

        # Parse request
        for item, package in traverse(proto_file):
            data = {
                'package': proto_file.package or '&lt;root&gt;',
                'filename': proto_file.name,
                'type': type(item),
                'item': item,
            }

            if isinstance(item, DescriptorProto):
                data.update({
                    'name': item.name,
                    'type': 'Message',
                    'properties': [{'name': f.name, 'type': f.type} for f in item.field],
                    'item': item,
                })
            elif isinstance(item, EnumDescriptorProto):
                data.update({
                    'name': item.name,
                    'type': 'Enum',
                    'values': [{'name': v.name, 'value': v.number} for v in item.value],
                    'item': item,
                })
            elif isinstance(item, ServiceDescriptorProto):
                data.update({
                    'name': item.name,
                    'type': 'Service',
                    'methods': item.method,
                    'item': item
                })


            # json.dump(data, STDERR, indent=2)
            sys.stderr.write('{}\n'.format(data))
            sys.stderr.write('-'*80+'\n')


    # Write to stdout. The protocol compiler will generate the files. 
    sys.stdout.write('')
