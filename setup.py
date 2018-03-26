#!/usr/bin/env python3

from distutils.core import setup

setup(
    name='dgrpc',
    version='0.1.0',
    description='A package which implements distributed agents using grpc.',
    author='Geoff Lawler',
    author_email='glawler@isi.edu',
    url='https://github.com/ISIEdgeLab/distributed_agents',
    download_url='https://github.com/ISIEdgeLab/distributed_agents',
    packages=['dgrpc'],
    requires=['PyYAML', 'grpcio'],
    scripts=['bin/agent_server.py'],
    data_files=[
        ('/etc/dgrpc', ['etc/dgrpc.conf']),
    ],
    classifiers=[
        'Development Status :: 1 - Alpha',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD',
        'Programming Language :: Python',
    ]
)
