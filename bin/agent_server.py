#!/usr/bin/env python3

from concurrent import futures
import logging
import time
import argparse
from subprocess import check_call, CalledProcessError
from os import path, geteuid

import grpc

from dgrpc import agent_server_pb2 as pb
from dgrpc import agent_server_pb2_grpc as pb_grpc

log = logging.getLogger(__name__)

def apt_install(deps):
    cmd = 'apt-get install -y {}'.format(' '.join(deps))
    try:
        log.info('attempting apt install via "{}"'.format(cmd))
        check_call(cmd.split(), close_fds=True)
    except CalledProcessError as e:
        return False

    log.info('successfully installed apt dependency "{}"'.format(' '.join(deps)))
    return True

def src_install(src_dir, script):
    cmd = [path.join(src_dir, script), src_dir, '/tmp']
    try:
        log.info('attemping src install via "{}"'.format(' '.join(cmd)))
        check_call(cmd, close_fds=True)
    except CalledProcessError as e:
        return False

    log.info('successfully installed src dependency "{}"'.format(script))
    return True

class AgentServerServicer(pb_grpc.AgentServerServicer):
    '''A simple class that loads agents and their dependencies.'''
    def __init__(self, server, config):
        log.debug('AgentServerServicer created.')
        self._server = server

        with open(config) as fd:
            self._config = yaml.load(fd)

        self._handle_init_config()

    def _handle_init_config(self):
        # load all pre-load dependencies and handle other initializtion things from the config file.
        if not 'logging' in self._config or not 'level' in self._config['logging']:
            level = logging.INFO
        else:
            level = self._config['logging']['level']

        if not 'logging' in self._config or not 'logfile' in self._config['logging']:
            logfile = path.join('/', 'var', 'log', 'dgrcp.log')
        else:
            logfile = self._config['logging']['logfile']

        logging.basicConfig(level=level, 
                            filename=logfile,
                            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                            datefmt='%m-%d %H:%M',
                            filemode='w')
        log.info('log level set to {}. loging to {}'.format(level, logfile))

        for agent, aconf in self._config['agents'].items():
            if aconf['dependencies']['when'] == 'preload':
                success, comment = self._load_dependencies(agent, aconf['dependencies']['how'])
                if not success:
                    log.critical('Unable to preload {} dependencies: {}'.format(agent, comment))
                    exit(99)   # what else to do?

    def Load(self, request, context):
        name = request.name

        log.info('Loading agent {}'.format(name))

        if not name in self._servicer_map:
            cmt = 'Unknown agent {}. Must be one of {}.'.format(
                name, ', '.join(self._config['agents'].keys()))
            return pb.Response(success=False, comment=cmt)

        # very hacky. This will need to be replaced. Only import the agents when they are being loaded. 
        # GTL TODO: make this load dynamically. Maybe via an IDL file...
        if name == 'TcpdumpAgent':
            from tcpdump_agent_servicer import AddServicer as AddTcpdumpService
            AddTcpdumpService(self._server)
        elif name == 'HttpServerAgent':
            from http_server_agent_servicer import AddServicer as AddHttpServerServicer
            AddHttpServerServicer(self._server)
        elif name == 'IperfAgent':
            from iperf_agent_servicer import AddServicer as AddIPerfServicer
            AddIPerfServicer(self._server)
        elif name == 'HttpClientAgent':
            from http_client_agent_servicer import AddServicer as AddHttpClientServicer
            AddHttpClientServicer(self._server)
        else:
            return pb.Response(success=False, comment='Unknown agent, {}, passed to agent server.'.format(name))
        
        log.info('{} loaded.'.format(name))
        return pb.Response(success=True, comment='{} loaded.'.format(name))

    def _load_dependencies(self, agent, installers):
        success = False
        for installer in installers:
            if 'apt' in installer and installer['apt']:
                if apt_install(installer['apt']):
                    success = True
                    break
            elif 'src' in installer and installer['src']:
                if src_install(self._config['dependency_sources'], installer['src']):
                    success = True
                    break
            else:
                return False, 'Misconfiguration: I do not know how to install dependencies like {}'.format(installer)
            
        if success:
            return True, 'Installed {} dependencies via a {} install.'.format(agent, installer)

        return False, 'Unable to install {} dependency using {}'.format(agent, installers)


def serve(port, poolsize, config):
    # We start with only one servicer loaded, namely a servicer which knows how
    # to load other servicers (agents). 
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=poolsize))
    server.add_insecure_port('[::]:{}'.format(port))
    agent_server = AgentServerServicer(server, config)
    pb_grpc.add_AgentServerServicer_to_server(agent_server, server)
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
    parser.add_argument('-c', '--config', type=str, default='/etc/dgrpc/dgrpc.conf',
                        help='Path to configration file. Default=/etc/dgprc/dgrpc.conf')
    args = parser.parse_args()

    if geteuid() != 0:
        exit('This needs to run as root.')

    # GTL - hacky, but the config file is YAML. 
    try:
        import yaml
    except ImportError:
        success = apt_install(['python3-yaml'])
        if not success:
            log.critical('Unable to install required python3 YAML library.')
            exit(99)

        import yaml

    serve(args.port, args.poolsize, args.config)
