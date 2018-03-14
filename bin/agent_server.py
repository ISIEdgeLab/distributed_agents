#!/usr/bin/env python3

from concurrent import futures
import logging
import time
import argparse
from subprocess import check_call, CalledProcessError

import grpc

import agent_server_pb2 as pb
import agent_server_pb2_grpc as pb_grpc

log = logging.getLogger(__name__)

class AgentServerServicer(pb_grpc.AgentServerServicer):
    '''A simple class that loads agents and their dependencies.'''
    def __init__(self, server):
        log.debug('AgentServerServicer created.')
        # we do not do dynamic loading at the moment. The servicer must know
        # at runtime about all agents and dependencies that can be loaded.
        self._servicer_map = {
            'IPerfAgent': {
                'dependencies': [
                    'iperf3'
                ]
            },
            'HttpServerAgent': {
                'dependencies': [
                    'apache2',
                    'libapache2-mod-wsgi',
                    'python-flask'
                ]
            },
            'TcpdumpAgent': {
                'dependencies': [
                    'python-netifaces', 'tcpdump'
                ]
            },
            'HttpClientAgent': {
                'dependencies': [
                    'curl',
                    'python3-pycurl',
                    # 'libdeterdash'
                ]
            }
        }
        self._server = server

    def Load(self, request, context):
        name = request.name

        log.info('Loading agent {}'.format(name))

        if not name in self._servicer_map:
            cmt = 'Unknown agent {}. Must be one of {}.'.format(
                name, ', '.join(self._servicer_map.keys()))
            return pb.Response(success=False, comment=cmt)

        # install dependencies then load the servicer.
        success, comment = self._install_dependencies(self._servicer_map[name]['dependencies'])
        if not success:
            return pb.Response(success=success, comment=comment)

        # very hacky. This will need to be replaced. Only import the agents when they are being loaded. 
        # GTL TODO: make this load dynamically. Maybe via an IDL file...
        if name in self._servicer_map:
            if name == 'TcpdumpAgent':
                from tcpdump_agent_servicer import AddServicer as AddTcpdumpService
                # self._servicer_map['TcpdumpAgent']['servicer'] = AddTcpdumpService
                AddTcpdumpService(self._server)
            elif name == 'HttpServerAgent':
                from http_server_agent_servicer import AddServicer as AddHttpServerServicer
                # self._servicer_map['HttpServerAgent']['servicer'] = AddHttpServerServicer
                AddHttpServerServicer(self._server)
            elif name == 'IperfAgent':
                from iperf_agent_servicer import AddServicer as AddIPerfServicer
                # self._servicer_map['IperfAgent']['servicer'] = AddIPerfServicer
                AddIPerfServicer(self._server)
            elif name == 'HttpClientAgent':
                from http_client_agent_servicer import AddServicer as AddHttpClientServicer
                # self._servicer_map['HttpClientAgent']['servicer'] = AddHttpClientServicer
                AddHttpClientServicer(self._server)
            else:
                return pb.Response(success=False, comment='Unknown agent, {}, passed to agent server.'.format(name))
        
        log.info('{} loaded.'.format(name))
        return pb.Response(success=True, comment='{} loaded.'.format(name))

    def _install_dependencies(self, deps):
        '''Install the given dependencies. Only support for APT at the moment.'''
        cmd = 'apt-get install -y {}'.format(' '.join(deps))
        try:
            check_call(cmd.split(), close_fds=True)
        except CalledProcessError as e:
            comment = 'Error installing dependencies {}'.format(' '.join(deps))
            log.error(comment)
            return False, comment

        return True, None

def serve(port, poolsize):
    # We start with only one servicer loaded, namely a servicer which knows how
    # to load other servicers (agents). 
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=poolsize))
    server.add_insecure_port('[::]:{}'.format(port))
    pb_grpc.add_AgentServerServicer_to_server(AgentServerServicer(server), server)
    server.start()

    # server.start() does not block, so do nothing while waiting for exit signal.
    _ONE_DAY_IN_SECONDS = 60 * 60 * 24
    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Start all configured agents on this machine.')
    parser.add_argument('-p', '--port', type=int, help='Port the agent server is listening on.', default=51000)
    parser.add_argument('--poolsize', type=int, default=10,
                        help='Number of threads to spawn to serve agent requests.')
    parser.add_argument('-v', '--verbose', default=False, action='store_true',
                        help='If given, turn on verbose logging.')
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    serve(args.port, args.poolsize)
